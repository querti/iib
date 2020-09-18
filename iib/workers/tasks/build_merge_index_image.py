# SPDX-License-Identifier: GPL-3.0-or-later
import logging
import tempfile

from iib.workers.api_utils import set_request_state
from iib.workers.tasks.build import (
    _add_ocp_label_to_index,
    _build_image,
    _cleanup,
    _create_and_push_manifest_list,
    _get_external_arch_pull_spec,
    get_image_label,
    _get_present_bundles,
    _get_resolved_image,
    _opm_index_add,
    _prepare_request_for_build,
    _push_image,
    _update_index_image_build_state,
    _update_index_image_pull_spec,
    _verify_index_image,
)
from iib.workers.tasks.celery import app
from iib.workers.tasks.utils import request_logger, run_cmd, set_registry_token


__all__ = ['handle_merge_request']

log = logging.getLogger(__name__)


def _add_bundles_missing_in_source(
    source_index_bundles,
    target_index_bundles,
    base_dir,
    binary_image,
    from_index,
    request_id,
    arch,
    ocp_version,
    overwrite_from_index_token=None,
):
    """
    Rebuild index image with bundles missing from source image but present in target image.

    If no bundles are missing in the source index image, the index image is still rebuilt
    using the new binary image.

    :param list source_index_bundles: bundles present in the source index image.
    :param list target_index_bundles: bundles present in the target index image.
    :param str base_dir: base directory where operation files will be located.
    :param str binary_image: binary image to be used by the new index image.
    :param str from_index: index image, whose data will be contained in the new index image.
    :param int request_id: the ID of the IIB build request.
    :param str arch: the architecture to build this image for.
    :param str ocp_version: ocp version which will be added as a label to the image.
    :param str overwrite_from_index_token: the token used for overwriting the input
        ``from_index`` image. This is required for non-privileged users to use
        ``overwrite_from_index``. The format of the token must be in the format "user:password".
    :return: bundles which were added to the index image.
    :rtype: list
    """
    set_request_state(request_id, 'in_progress', 'Adding bundles missing in source index image')
    log.info('Adding bundles from target index image which are missing from source index image')
    missing_bundles = []
    source_bundle_digests = []
    target_bundle_digests = []

    for bundle in source_index_bundles:
        if '@sha256:' in bundle['bundlePath']:
            source_bundle_digests.append(bundle['bundlePath'].split('@sha256:')[-1])
    for bundle in target_index_bundles:
        if '@sha256:' in bundle['bundlePath']:
            target_bundle_digests.append((bundle['bundlePath'].split('@sha256:')[-1], bundle))

    for target_bundle_digest, bundle in target_bundle_digests:
        if target_bundle_digest not in source_bundle_digests:
            missing_bundles.append(bundle)

    missing_bundle_paths = [bundle['bundlePath'] for bundle in missing_bundles]
    if missing_bundle_paths:
        log.info('%s bundles are missing in the source index image.', len(missing_bundle_paths))
    else:
        log.info(
            'No bundles are missing in the source index image. However, the index image is '
            'still being rebuilt with the new binary image.'
        )

    _opm_index_add(
        base_dir, missing_bundle_paths, binary_image, from_index, overwrite_from_index_token
    )
    _add_ocp_label_to_index(ocp_version, base_dir, 'index.Dockerfile')
    _build_image(base_dir, 'index.Dockerfile', request_id, arch)
    _push_image(request_id, arch)
    _create_and_push_manifest_list(request_id, [arch])
    log.info('New index image created')

    return missing_bundles


def _get_bundles_from_deprecation_list(bundles, deprecation_list):
    """
    Get a list of to-be-deprecated bundles based on the data from the deprecation list.

    :param list bundles: list of bundles to apply the filter on.
    :param list deprecation_list: list of deprecated bundle pull specifications (digest).
    :return: bundles which are to be deprecated.
    :rtype: list
    """
    deprecate_bundles = []
    for bundle in bundles:
        if '@sha256:' in bundle['bundlePath']:
            resolved_bundle = bundle['bundlePath']
        else:
            resolved_bundle = _get_resolved_image(bundle['bundlePath'])
        if resolved_bundle in deprecation_list:
            deprecate_bundles.append(resolved_bundle)

    log.info(
        'Bundles that will be deprecated from the index image: %s', ','.join(deprecate_bundles)
    )
    return deprecate_bundles


def _get_deprecated_bundles_by_ocp_version(bundles_with_ocp_version, ocp_version):
    """
    Parse ocp version and determine if the bundles should be deprecated.

    :param list bundles_with_ocp_version: list of tuples containing bundles and their supported
        ocp versions.
    :param str ocp_version: ocp version by which to filter the bundles.
    :return: bundles which don't satisfy the ocp version.
    :rtype: list
    """
    ocp_version = [int(num) for num in ocp_version.replace('v', '').split('.')]
    deprecate_bundles = []
    for bundle, bundle_ocp_version in bundles_with_ocp_version:
        # only one version
        if bundle_ocp_version[0] == '=':
            accepted_version = [
                int(num) for num in bundle_ocp_version.replace('=', '').replace('v', '').split('.')
            ]
            if ocp_version != accepted_version:
                deprecate_bundles.append(bundle)
        # version range
        elif '-' in bundle_ocp_version:
            min_version, max_version = [
                ver.split('.') for ver in bundle_ocp_version.replace('v', '').split('-')
            ]
            min_version = [int(num) for num in min_version]
            max_version = [int(num) for num in max_version]
            if ocp_version < min_version or ocp_version > max_version:
                deprecate_bundles.append(bundle)
        # multiple csv versions
        elif ',' in bundle_ocp_version:
            str_versions = [
                version.split('.') for version in bundle_ocp_version.replace('v', '').split(',')
            ]
            versions = []
            for version in str_versions:
                versions.append([int(num) for num in version])
            min_version = sorted(versions)[0]
            if ocp_version < min_version:
                deprecate_bundles.append(bundle)
        # minimum version
        else:
            min_version = [int(num) for num in bundle_ocp_version.replace('v', '').split('.')]
            if ocp_version < min_version:
                deprecate_bundles.append(bundle)

    return deprecate_bundles


def _check_operator_heads_for_deprecation(bundles, ocp_version):
    """
    Calculate the head of each operator and determine whether they should be deprecated.

    :param list bundles: list of bundles to extract the data from.
    :param str ocp_version: ocp version to classify deprecation.
    :return: list of bundles to be deprecated.
    :rtype: list
    """
    operators_bundles_asoc = {}
    for bundle in bundles:
        if bundle['channelName'] not in operators_bundles_asoc:
            operators_bundles_asoc[bundle['channelName']] = []
        operators_bundles_asoc[bundle['channelName']].append(bundle)

    channel_heads = []
    for bundles in operators_bundles_asoc.values():
        # comparing versions as strings seems the safest
        channel_heads.append(sorted(bundles, key=lambda x: x['version'], reverse=True)[0])

    bundles_with_ocp_version = []
    for head_bundle in channel_heads:
        ocp_versions = get_image_label(head_bundle['bundlePath'], 'com.redhat.openshift.versions')
        bundles_with_ocp_version.append((head_bundle, ocp_versions))

    return _get_deprecated_bundles_by_ocp_version(bundles_with_ocp_version, ocp_version)


def _deprecate_bundles(
    bundles, base_dir, binary_image, from_index, ocp_version, overwrite_from_index_token=None,
):
    """
    Deprecate specified bundles from index image. Only Dockerfile is created, no build is performed.

    :param list bundles: pull specifications of bundles to deprecate.
    :param str base_dir: base directory where operation files will be located.
    :param str binary_image: binary image to be used by the new index image.
    :param str from_index: index image, from which the bundles will be deprecated.
    :param str ocp_version: ocp version which will be added as a label to the image.
    :param str overwrite_from_index_token: the token used for overwriting the input
        ``from_index`` image. This is required for non-privileged users to use
        ``overwrite_from_index``. The format of the token must be in the format "user:password".
    """
    cmd = [
        'opm',
        'index',
        'deprecatetruncate',
        '--generate',
        '--binary-image',
        binary_image,
        '--from-index',
        from_index,
        '--bundles',
        ','.join(bundles),
    ]
    # TODO catch error of default channel deletion
    with set_registry_token(overwrite_from_index_token, from_index):
        run_cmd(
            cmd, {'cwd': base_dir}, exc_msg='Failed to deprecate the bundles',
        )

    _add_ocp_label_to_index(ocp_version, base_dir, 'index.Dockerfile')


@app.task
@request_logger
def handle_merge_request(
    binary_image,
    source_from_index,
    target_index,
    deprecation_list,
    request_id,
    overwrite_from_index=False,
    overwrite_from_index_token=None,
):
    """
    Coordinate the work needed to merge old (N) index image with new (N+1) index image.

    :param str binary_image: the pull specification of the container image where the opm binary
        gets copied from.
    :param str source_from_index: pull specification to be used as base for building the new
        index image.
    :param str target_index: pull specification of content stage index image for the
        corresponding target index image.
    :param list deprecation_list: List of deprecated bundles for the target index image tag.
    :param int request_id: the ID of the IIB build request.
    :param bool overwrite_from_index: if True, overwrite the input ``target_index`` with
        the built index image.
    :param str overwrite_from_index_token: the token used for overwriting the input
        ``target_index`` image. This is required for non-privileged users to use
        ``overwrite_from_index``. The format of the token must be in the format "user:password".
    :raises IIBError: if the index image merge fails.
    """
    _cleanup()
    prebuild_info = _prepare_request_for_build(
        binary_image,
        request_id,
        overwrite_from_index_token=overwrite_from_index_token,
        source_from_index=source_from_index,
        target_index=target_index,
    )
    _update_index_image_build_state(request_id, prebuild_info)

    with tempfile.TemporaryDirectory(prefix='iib-') as temp_dir:
        set_request_state(request_id, 'in_progress', 'Getting bundles present in the index images')
        log.info('Getting bundles present in the source index image')
        source_index_bundles = _get_present_bundles(source_from_index, temp_dir)
        log.info('Getting bundles present in the target index image')
        target_index_bundles = _get_present_bundles(target_index, temp_dir)

        arches = list(prebuild_info['arches'])
        arch = 'amd64' if 'amd64' in arches else arches[0]

        missing_bundles = _add_bundles_missing_in_source(
            source_index_bundles,
            target_index_bundles,
            temp_dir,
            binary_image,
            source_from_index,
            request_id,
            arch,
            prebuild_info['target_ocp_version'],
            overwrite_from_index_token,
        )

        set_request_state(request_id, 'in_progress', 'Deprecating bundles in the deprecation list')
        log.info('Deprecating bundles in the deprecation list')
        intermediate_bundles = source_index_bundles + missing_bundles
        deprecate_bundles = _get_bundles_from_deprecation_list(
            intermediate_bundles, deprecation_list,
        )
        intermediate_image_name = _get_external_arch_pull_spec(
            request_id, arch, include_transport=False
        )

        if deprecate_bundles:
            _deprecate_bundles(
                deprecate_bundles,
                temp_dir,
                binary_image,
                intermediate_image_name,
                prebuild_info['target_ocp_version'],
                overwrite_from_index_token,
            )

        for arch in sorted(prebuild_info['arches']):
            _build_image(temp_dir, 'index.Dockerfile', request_id, arch)
            _push_image(request_id, arch)

    _verify_index_image(
        prebuild_info['source_from_index_resolved'], source_from_index, overwrite_from_index_token
    )
    _verify_index_image(
        prebuild_info['target_index_resolved'], target_index, overwrite_from_index_token
    )

    output_pull_spec = _create_and_push_manifest_list(request_id, prebuild_info['arches'])
    _update_index_image_pull_spec(
        output_pull_spec,
        request_id,
        prebuild_info['arches'],
        target_index,
        overwrite_from_index,
        overwrite_from_index_token,
    )
