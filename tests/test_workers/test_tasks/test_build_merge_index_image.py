# SPDX-License-Identifier: GPL-3.0-or-later
from unittest import mock

import pytest

from iib.workers.tasks import build_merge_index_image


@mock.patch('iib.workers.tasks.build_merge_index_image._update_index_image_pull_spec')
@mock.patch('iib.workers.tasks.build_merge_index_image._verify_index_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._create_and_push_manifest_list')
@mock.patch('iib.workers.tasks.build_merge_index_image._push_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._build_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._deprecate_bundles')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_external_arch_pull_spec')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_bundles_from_deprecation_list')
@mock.patch('iib.workers.tasks.build_merge_index_image._add_bundles_missing_in_source')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_present_bundles')
@mock.patch('iib.workers.tasks.build_merge_index_image.set_request_state')
@mock.patch('iib.workers.tasks.build_merge_index_image._update_index_image_build_state')
@mock.patch('iib.workers.tasks.build_merge_index_image._prepare_request_for_build')
@mock.patch('iib.workers.tasks.build_merge_index_image._cleanup')
def test_handle_merge_request(
    mock_cleanup,
    mock_prfb,
    mock_uiibs,
    mock_srs,
    mock_gpb,
    mock_abmis,
    mock_gbfdl,
    mock_geaps,
    mock_dep_b,
    mock_bi,
    mock_pi,
    mock_capml,
    mock_vii,
    mock_uiips,
):
    prebuild_info = {
        'arches': {'amd64', 'other_arch'},
        'target_ocp_version': '4.6',
        'source_from_index_resolved': 'source-index@sha256:resolved',
        'target_index_resolved': 'target-index@sha256:resolved',
    }
    mock_prfb.return_value = prebuild_info
    mock_gbfdl.return_value = ['some-bundle:1.0']

    build_merge_index_image.handle_merge_request(
        'binary-image:1.0',
        'source-from-index:1.0',
        'target-from-index:1.0',
        ['some-bundle:1.0'],
        1,
    )

    mock_cleanup.assert_called_once()
    mock_prfb.assert_called_once_with(
        'binary-image:1.0',
        1,
        overwrite_from_index_token=None,
        source_from_index='source-from-index:1.0',
        target_index='target-from-index:1.0',
    )
    mock_uiibs.assert_called_once_with(1, prebuild_info)
    assert mock_gpb.call_count == 2
    mock_abmis.assert_called_once()
    mock_gbfdl.assert_called_once()
    mock_geaps.assert_called_once()
    mock_dep_b.assert_called_once()
    assert mock_bi.call_count == 2
    assert mock_pi.call_count == 2
    assert mock_vii.call_count == 2
    assert mock_capml.call_count == 1
    mock_uiips.assert_called_once()


@mock.patch('iib.workers.tasks.build_merge_index_image._update_index_image_pull_spec')
@mock.patch('iib.workers.tasks.build_merge_index_image._verify_index_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._create_and_push_manifest_list')
@mock.patch('iib.workers.tasks.build_merge_index_image._push_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._build_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._deprecate_bundles')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_external_arch_pull_spec')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_bundles_from_deprecation_list')
@mock.patch('iib.workers.tasks.build_merge_index_image._add_bundles_missing_in_source')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_present_bundles')
@mock.patch('iib.workers.tasks.build_merge_index_image.set_request_state')
@mock.patch('iib.workers.tasks.build_merge_index_image._update_index_image_build_state')
@mock.patch('iib.workers.tasks.build_merge_index_image._prepare_request_for_build')
@mock.patch('iib.workers.tasks.build_merge_index_image._cleanup')
def test_handle_merge_request_no_deprecate(
    mock_cleanup,
    mock_prfb,
    mock_uiibs,
    mock_srs,
    mock_gpb,
    mock_abmis,
    mock_gbfdl,
    mock_geaps,
    mock_dep_b,
    mock_bi,
    mock_pi,
    mock_capml,
    mock_vii,
    mock_uiips,
):
    prebuild_info = {
        'arches': {'amd64', 'other_arch'},
        'target_ocp_version': '4.6',
        'source_from_index_resolved': 'source-index@sha256:resolved',
        'target_index_resolved': 'target-index@sha256:resolved',
    }
    mock_prfb.return_value = prebuild_info
    mock_gbfdl.return_value = []

    build_merge_index_image.handle_merge_request(
        'binary-image:1.0',
        'source-from-index:1.0',
        'target-from-index:1.0',
        ['some-bundle:1.0'],
        1,
    )

    mock_cleanup.assert_called_once()
    mock_prfb.assert_called_once_with(
        'binary-image:1.0',
        1,
        overwrite_from_index_token=None,
        source_from_index='source-from-index:1.0',
        target_index='target-from-index:1.0',
    )
    mock_uiibs.assert_called_once_with(1, prebuild_info)
    assert mock_gpb.call_count == 2
    mock_abmis.assert_called_once()
    mock_gbfdl.assert_called_once()
    mock_geaps.assert_called_once()
    assert mock_dep_b.call_count == 0
    assert mock_bi.call_count == 2
    assert mock_pi.call_count == 2
    assert mock_vii.call_count == 2
    mock_capml.assert_called_once()
    mock_uiips.assert_called_once()


@mock.patch('iib.workers.tasks.build_merge_index_image._create_and_push_manifest_list')
@mock.patch('iib.workers.tasks.build_merge_index_image._push_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._build_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._add_ocp_label_to_index')
@mock.patch('iib.workers.tasks.build_merge_index_image._opm_index_add')
@mock.patch('iib.workers.tasks.build_merge_index_image.set_request_state')
def test_add_bundles_missing_in_source(
    mock_srs, mock_oia, mock_aolti, mock_bi, mock_pi, mock_capml
):
    source_bundles = [
        {'packageName': 'bundle1', 'version': '1.0', 'bundlePath': 'quay.io/bundle1@sha256:123456'},
        {'packageName': 'bundle2', 'version': '2.0', 'bundlePath': 'quay.io/bundle2@sha256:234567'},
    ]
    target_bundles = [
        {'packageName': 'bundle1', 'version': '1.0', 'bundlePath': 'quay.io/bundle1@sha256:123456'},
        {'packageName': 'bundle3', 'version': '3.0', 'bundlePath': 'quay.io/bundle3@sha256:456789'},
        {'packageName': 'bundle4', 'version': '4.0', 'bundlePath': 'quay.io/bundle4@sha256:567890'},
    ]
    missing_bundles = build_merge_index_image._add_bundles_missing_in_source(
        source_bundles,
        target_bundles,
        'some_dir',
        'binary-image:4.5',
        'index-image:4.6',
        1,
        'amd64',
        '4.6',
    )
    assert missing_bundles == [
        {'packageName': 'bundle3', 'version': '3.0', 'bundlePath': 'quay.io/bundle3@sha256:456789'},
        {'packageName': 'bundle4', 'version': '4.0', 'bundlePath': 'quay.io/bundle4@sha256:567890'},
    ]
    mock_srs.assert_called_once()
    mock_oia.assert_called_once_with(
        'some_dir',
        ['quay.io/bundle3@sha256:456789', 'quay.io/bundle4@sha256:567890'],
        'binary-image:4.5',
        'index-image:4.6',
        None,
    )
    mock_aolti.assert_called_once()
    mock_bi.assert_called_once()
    mock_pi.assert_called_once()
    mock_capml.assert_called_once()


@mock.patch('iib.workers.tasks.build_merge_index_image._create_and_push_manifest_list')
@mock.patch('iib.workers.tasks.build_merge_index_image._push_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._build_image')
@mock.patch('iib.workers.tasks.build_merge_index_image._add_ocp_label_to_index')
@mock.patch('iib.workers.tasks.build_merge_index_image._opm_index_add')
@mock.patch('iib.workers.tasks.build_merge_index_image.set_request_state')
def test_add_bundles_missing_in_source_none_missing(
    mock_srs, mock_oia, mock_aolti, mock_bi, mock_pi, mock_capml
):
    source_bundles = [
        {'packageName': 'bundle1', 'version': '1.0', 'bundlePath': 'quay.io/bundle1:123456'},
        {'packageName': 'bundle2', 'version': '2.0', 'bundlePath': 'quay.io/bundle2:123456'},
        {'packageName': 'bundle3', 'version': '3.0', 'bundlePath': 'quay.io/bundle3:123456'},
        {'packageName': 'bundle4', 'version': '4.0', 'bundlePath': 'quay.io/bundle4:123456'},
    ]
    target_bundles = [
        {'packageName': 'bundle1', 'version': '1.0', 'bundlePath': 'quay.io/bundle1:123456'},
        {'packageName': 'bundle2', 'version': '2.0', 'bundlePath': 'quay.io/bundle2:123456'},
    ]
    missing_bundles = build_merge_index_image._add_bundles_missing_in_source(
        source_bundles,
        target_bundles,
        'some_dir',
        'binary-image:4.5',
        'index-image:4.6',
        1,
        'amd64',
        '4.6',
    )
    assert missing_bundles == []
    mock_srs.assert_called_once()
    mock_oia.assert_called_once()
    mock_aolti.assert_called_once()
    mock_bi.assert_called_once()
    mock_pi.assert_called_once()
    mock_capml.assert_called_once()


@mock.patch('iib.workers.tasks.build_merge_index_image._get_resolved_image')
def test_get_bundles_from_deprecation_list(mock_gri):
    present_bundles = [
        {'packageName': 'bundle1', 'version': '1.0', 'bundlePath': 'quay.io/bundle1@sha256:123456'},
        {'packageName': 'bundle2', 'version': '2.0', 'bundlePath': 'quay.io/bundle2:2'},
        {'packageName': 'bundle3', 'version': '3.0', 'bundlePath': 'quay.io/bundle3:3'},
    ]
    deprecation_list = [
        'quay.io/bundle1@sha256:123456',
        'quay.io/bundle2@sha256:987654',
        'quay.io/bundle4@sha256:1a2bcd',
    ]
    mock_gri.side_effect = ['quay.io/bundle2@sha256:987654', 'quay.io/bundle3@sha256:abcdef']
    deprecate_bundles = build_merge_index_image._get_bundles_from_deprecation_list(
        present_bundles, deprecation_list
    )
    assert deprecate_bundles == ['quay.io/bundle1@sha256:123456', 'quay.io/bundle2@sha256:987654']
    assert mock_gri.call_count == 2


@pytest.mark.parametrize(
    'bundles_with_metadata, ocp_version, expected_deprecated_bundles',
    (
        (
            [
                (
                    {
                        'packageName': 'bundle1',
                        'version': '1.0',
                        'bundlePath': 'quay.io/bundle1@sha256:123456',
                    },
                    '=v4.6',
                ),
                (
                    {
                        'packageName': 'bundle2',
                        'version': '2.0',
                        'bundlePath': 'quay.io/bundle2@sha256:654321',
                    },
                    '=v4.5',
                ),
                (
                    {
                        'packageName': 'bundle3',
                        'version': '3.0',
                        'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                    },
                    '=v4.5',
                ),
            ],
            'v4.6',
            [
                {
                    'packageName': 'bundle2',
                    'version': '2.0',
                    'bundlePath': 'quay.io/bundle2@sha256:654321',
                },
                {
                    'packageName': 'bundle3',
                    'version': '3.0',
                    'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                },
            ],
        ),
        (
            [
                (
                    {
                        'packageName': 'bundle1',
                        'version': '1.0',
                        'bundlePath': 'quay.io/bundle1@sha256:123456',
                    },
                    'v4.4-v4.6',
                ),
                (
                    {
                        'packageName': 'bundle2',
                        'version': '2.0',
                        'bundlePath': 'quay.io/bundle2@sha256:654321',
                    },
                    'v4.7-v4.8',
                ),
                (
                    {
                        'packageName': 'bundle3',
                        'version': '3.0',
                        'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                    },
                    'v4.5-v4.7',
                ),
            ],
            'v4.5',
            [
                {
                    'packageName': 'bundle2',
                    'version': '2.0',
                    'bundlePath': 'quay.io/bundle2@sha256:654321',
                }
            ],
        ),
        (
            [
                (
                    {
                        'packageName': 'bundle1',
                        'version': '1.0',
                        'bundlePath': 'quay.io/bundle1@sha256:123456',
                    },
                    'v4.5,v4.6',
                ),
                (
                    {
                        'packageName': 'bundle2',
                        'version': '2.0',
                        'bundlePath': 'quay.io/bundle2@sha256:654321',
                    },
                    'v4.4,v4.5',
                ),
                (
                    {
                        'packageName': 'bundle3',
                        'version': '3.0',
                        'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                    },
                    'v4.7,v4.8,v4.9',
                ),
                (
                    {
                        'packageName': 'bundle4',
                        'version': '4.0',
                        'bundlePath': 'quay.io/bundle4@sha256:fedcba',
                    },
                    'v4.6,v4.7,v4.8',
                ),
            ],
            'v4.6',
            [
                {
                    'packageName': 'bundle3',
                    'version': '3.0',
                    'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                },
            ],
        ),
        (
            [
                (
                    {
                        'packageName': 'bundle1',
                        'version': '1.0',
                        'bundlePath': 'quay.io/bundle1@sha256:123456',
                    },
                    'v4.5',
                ),
                (
                    {
                        'packageName': 'bundle2',
                        'version': '2.0',
                        'bundlePath': 'quay.io/bundle2@sha256:654321',
                    },
                    'v4.6',
                ),
                (
                    {
                        'packageName': 'bundle3',
                        'version': '3.0',
                        'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                    },
                    'v4.7',
                ),
            ],
            'v4.6',
            [
                {
                    'packageName': 'bundle3',
                    'version': '3.0',
                    'bundlePath': 'quay.io/bundle3@sha256:abcdef',
                },
            ],
        ),
    ),
)
def test_get_deprecated_bundles_by_ocp_version(
    bundles_with_metadata, ocp_version, expected_deprecated_bundles
):
    deprecate_bundles = build_merge_index_image._get_deprecated_bundles_by_ocp_version(
        bundles_with_metadata, ocp_version
    )
    assert deprecate_bundles == expected_deprecated_bundles


@mock.patch('iib.workers.tasks.build_merge_index_image.get_image_label')
@mock.patch('iib.workers.tasks.build_merge_index_image._get_deprecated_bundles_by_ocp_version')
def test_check_operator_heads_for_deprecation(mock_gdbbov, mock_gil):
    bundles = [
        {
            'packageName': 'bundle1',
            'version': '1.0',
            'bundlePath': 'quay.io/bundle1@sha256:abcdef',
            'channelName': 'channel1',
        },
        {
            'packageName': 'bundle1',
            'version': '1.6',
            'bundlePath': 'quay.io/bundle1@sha256:fedcba',
            'channelName': 'channel1',
        },
        {
            'packageName': 'bundle2',
            'version': '3.4',
            'bundlePath': 'quay.io/bundle2@sha256:123456',
            'channelName': 'channel2',
        },
        {
            'packageName': 'bundle2',
            'version': '3.5',
            'bundlePath': 'quay.io/bundle2@sha256:654321',
            'channelName': 'channel2',
        },
    ]
    mock_gil.side_effect = ['v4.6', 'v4.7']
    build_merge_index_image._check_operator_heads_for_deprecation(bundles, 'v4.6')
    assert mock_gil.call_count == 2
    mock_gdbbov.assert_called_once_with(
        [
            (
                {
                    'packageName': 'bundle1',
                    'version': '1.6',
                    'bundlePath': 'quay.io/bundle1@sha256:fedcba',
                    'channelName': 'channel1',
                },
                'v4.6',
            ),
            (
                {
                    'packageName': 'bundle2',
                    'version': '3.5',
                    'bundlePath': 'quay.io/bundle2@sha256:654321',
                    'channelName': 'channel2',
                },
                'v4.7',
            ),
        ],
        'v4.6',
    )


@mock.patch('iib.workers.tasks.build_merge_index_image._add_ocp_label_to_index')
@mock.patch('iib.workers.tasks.build_merge_index_image.run_cmd')
@mock.patch('iib.workers.tasks.build_merge_index_image.set_registry_token')
def test_deprecate_bundles(mock_srt, mock_run_cmd, mock_aolti):
    bundles = ['quay.io/bundle1:1.0', 'quay.io/bundle2:2.0']
    from_index = 'quay.io/index-image:4.6'
    binary_image = 'quay.io/binary-image:4.6'
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
    build_merge_index_image._deprecate_bundles(
        bundles, 'some_dir', binary_image, from_index, '4.6',
    )
    mock_run_cmd.assert_called_once_with(
        cmd, {'cwd': 'some_dir'}, exc_msg='Failed to deprecate the bundles'
    )
    mock_aolti.assert_called_once_with('4.6', 'some_dir', 'index.Dockerfile')
