from __future__ import annotations

import logging
import re

import cfgv
import pytest

import pre_commit.constants as C
from pre_commit.clientlib import check_type_tag
from pre_commit.clientlib import CONFIG_HOOK_DICT
from pre_commit.clientlib import CONFIG_REPO_DICT
from pre_commit.clientlib import CONFIG_SCHEMA
from pre_commit.clientlib import DEFAULT_LANGUAGE_VERSION
from pre_commit.clientlib import InvalidManifestError
from pre_commit.clientlib import load_manifest
from pre_commit.clientlib import MANIFEST_HOOK_DICT
from pre_commit.clientlib import MANIFEST_SCHEMA
from pre_commit.clientlib import META_HOOK_DICT
from pre_commit.clientlib import OptionalSensibleRegexAtHook
from pre_commit.clientlib import OptionalSensibleRegexAtTop
from pre_commit.clientlib import parse_version
from testing.fixtures import sample_local_config


def is_valid_according_to_schema(obj, obj_schema):
    try:
        cfgv.validate(obj, obj_schema)
        return True
    except cfgv.ValidationError:
        return False


@pytest.mark.parametrize('value', ('definitely-not-a-tag', 'fiel'))
def test_check_type_tag_failures(value):
    with pytest.raises(cfgv.ValidationError):
        check_type_tag(value)


def test_check_type_tag_success():
    check_type_tag('file')


@pytest.mark.parametrize(
    'cfg',
    (
        {
            'repos': [{
                'repo': 'git@github.com:pre-commit/pre-commit-hooks',
                'rev': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
                'hooks': [{'id': 'pyflakes', 'files': '\\.py$'}],
            }],
        },
        {
            'repos': [{
                'repo': 'git@github.com:pre-commit/pre-commit-hooks',
                'rev': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
                'hooks': [
                    {
                        'id': 'pyflakes',
                        'files': '\\.py$',
                        'args': ['foo', 'bar', 'baz'],
                    },
                ],
            }],
        },
    ),
)
def test_config_valid(cfg):
    assert is_valid_according_to_schema(cfg, CONFIG_SCHEMA)


def test_invalid_config_wrong_type():
    cfg = {
        'repos': [{
            'repo': 'git@github.com:pre-commit/pre-commit-hooks',
            'rev': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
            'hooks': [
                {
                    'id': 'pyflakes',
                    'files': '\\.py$',
                    # Exclude pattern must be a string
                    'exclude': 0,
                    'args': ['foo', 'bar', 'baz'],
                },
            ],
        }],
    }
    assert not is_valid_according_to_schema(cfg, CONFIG_SCHEMA)


def test_local_hooks_with_rev_fails():
    config_obj = {'repos': [dict(sample_local_config(), rev='foo')]}
    with pytest.raises(cfgv.ValidationError):
        cfgv.validate(config_obj, CONFIG_SCHEMA)


def test_config_with_local_hooks_definition_passes():
    config_obj = {'repos': [sample_local_config()]}
    cfgv.validate(config_obj, CONFIG_SCHEMA)


def test_config_schema_does_not_contain_defaults():
    """Due to the way our merging works, if this schema has any defaults they
    will clobber potentially useful values in the backing manifest. #227
    """
    for item in CONFIG_HOOK_DICT.items:
        assert not isinstance(item, cfgv.Optional)


def test_ci_map_key_allowed_at_top_level(caplog):
    cfg = {
        'ci': {'skip': ['foo']},
        'repos': [{'repo': 'meta', 'hooks': [{'id': 'identity'}]}],
    }
    cfgv.validate(cfg, CONFIG_SCHEMA)
    assert not caplog.record_tuples


def test_ci_key_must_be_map():
    with pytest.raises(cfgv.ValidationError):
        cfgv.validate({'ci': 'invalid', 'repos': []}, CONFIG_SCHEMA)


@pytest.mark.parametrize(
    'rev',
    (
        'v0.12.4',
        'b27f281',
        'b27f281eb9398fc8504415d7fbdabf119ea8c5e1',
        '19.10b0',
        '4.3.21-2',
    ),
)
def test_warn_mutable_rev_ok(caplog, rev):
    config_obj = {
        'repo': 'https://gitlab.com/pycqa/flake8',
        'rev': rev,
        'hooks': [{'id': 'flake8'}],
    }
    cfgv.validate(config_obj, CONFIG_REPO_DICT)

    assert caplog.record_tuples == []


@pytest.mark.parametrize(
    'rev',
    (
        '',
        'HEAD',
        'stable',
        'master',
        'some_branch_name',
    ),
)
def test_warn_mutable_rev_invalid(caplog, rev):
    config_obj = {
        'repo': 'https://gitlab.com/pycqa/flake8',
        'rev': rev,
        'hooks': [{'id': 'flake8'}],
    }
    cfgv.validate(config_obj, CONFIG_REPO_DICT)

    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            "The 'rev' field of repo 'https://gitlab.com/pycqa/flake8' "
            'appears to be a mutable reference (moving tag / branch).  '
            'Mutable references are never updated after first install and are '
            'not supported.  '
            'See https://pre-commit.com/#using-the-latest-version-for-a-repository '  # noqa: E501
            'for more details.  '
            'Hint: `pre-commit autoupdate` often fixes this.',
        ),
    ]


def test_warn_mutable_rev_conditional():
    config_obj = {
        'repo': 'meta',
        'rev': '3.7.7',
        'hooks': [{'id': 'flake8'}],
    }

    with pytest.raises(cfgv.ValidationError):
        cfgv.validate(config_obj, CONFIG_REPO_DICT)


@pytest.mark.parametrize(
    'validator_cls',
    (
        OptionalSensibleRegexAtHook,
        OptionalSensibleRegexAtTop,
    ),
)
def test_sensible_regex_validators_dont_pass_none(validator_cls):
    validator = validator_cls('files', cfgv.check_string)
    with pytest.raises(cfgv.ValidationError) as excinfo:
        validator.check({'files': None})

    assert str(excinfo.value) == (
        '\n'
        '==> At key: files'
        '\n'
        '=====> Expected string got NoneType'
    )


@pytest.mark.parametrize(
    ('regex', 'warning'),
    (
        (
            r'dir/*.py',
            "The 'files' field in hook 'flake8' is a regex, not a glob -- "
            "matching '/*' probably isn't what you want here",
        ),
        (
            r'dir[\/].*\.py',
            r"pre-commit normalizes slashes in the 'files' field in hook "
            r"'flake8' to forward slashes, so you can use / instead of [\/]",
        ),
        (
            r'dir[/\\].*\.py',
            r"pre-commit normalizes slashes in the 'files' field in hook "
            r"'flake8' to forward slashes, so you can use / instead of [/\\]",
        ),
        (
            r'dir[\\/].*\.py',
            r"pre-commit normalizes slashes in the 'files' field in hook "
            r"'flake8' to forward slashes, so you can use / instead of [\\/]",
        ),
    ),
)
def test_validate_optional_sensible_regex_at_hook(caplog, regex, warning):
    config_obj = {
        'id': 'flake8',
        'files': regex,
    }
    cfgv.validate(config_obj, CONFIG_HOOK_DICT)

    assert caplog.record_tuples == [('pre_commit', logging.WARNING, warning)]


def test_validate_optional_sensible_regex_at_local_hook(caplog):
    config_obj = sample_local_config()
    config_obj['hooks'][0]['files'] = 'dir/*.py'

    cfgv.validate(config_obj, CONFIG_REPO_DICT)

    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            "The 'files' field in hook 'do_not_commit' is a regex, not a glob "
            "-- matching '/*' probably isn't what you want here",
        ),
    ]


def test_validate_optional_sensible_regex_at_meta_hook(caplog):
    config_obj = {
        'repo': 'meta',
        'hooks': [{'id': 'identity', 'files': 'dir/*.py'}],
    }

    cfgv.validate(config_obj, CONFIG_REPO_DICT)

    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            "The 'files' field in hook 'identity' is a regex, not a glob "
            "-- matching '/*' probably isn't what you want here",
        ),
    ]


@pytest.mark.parametrize(
    ('regex', 'warning'),
    (
        (
            r'dir/*.py',
            "The top-level 'files' field is a regex, not a glob -- "
            "matching '/*' probably isn't what you want here",
        ),
        (
            r'dir[\/].*\.py',
            r"pre-commit normalizes the slashes in the top-level 'files' "
            r'field to forward slashes, so you can use / instead of [\/]',
        ),
        (
            r'dir[/\\].*\.py',
            r"pre-commit normalizes the slashes in the top-level 'files' "
            r'field to forward slashes, so you can use / instead of [/\\]',
        ),
        (
            r'dir[\\/].*\.py',
            r"pre-commit normalizes the slashes in the top-level 'files' "
            r'field to forward slashes, so you can use / instead of [\\/]',
        ),
    ),
)
def test_validate_optional_sensible_regex_at_top_level(caplog, regex, warning):
    config_obj = {
        'files': regex,
        'repos': [],
    }
    cfgv.validate(config_obj, CONFIG_SCHEMA)

    assert caplog.record_tuples == [('pre_commit', logging.WARNING, warning)]


def test_invalid_stages_error():
    cfg = {'repos': [sample_local_config()]}
    cfg['repos'][0]['hooks'][0]['stages'] = ['invalid']

    with pytest.raises(cfgv.ValidationError) as excinfo:
        cfgv.validate(cfg, CONFIG_SCHEMA)

    assert str(excinfo.value) == (
        '\n'
        '==> At Config()\n'
        '==> At key: repos\n'
        "==> At Repository(repo='local')\n"
        '==> At key: hooks\n'
        "==> At Hook(id='do_not_commit')\n"
        # this line was missing due to the custom validator
        '==> At key: stages\n'
        '==> At index 0\n'
        "=====> Expected one of commit-msg, manual, post-checkout, post-commit, post-merge, post-rewrite, pre-commit, pre-merge-commit, pre-push, pre-rebase, prepare-commit-msg but got: 'invalid'"  # noqa: E501
    )


def test_warning_for_deprecated_stages(caplog):
    config_obj = sample_local_config()
    config_obj['hooks'][0]['stages'] = ['commit', 'push']

    cfgv.validate(config_obj, CONFIG_REPO_DICT)

    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            'hook id `do_not_commit` uses deprecated stage names '
            '(commit, push) which will be removed in a future version.  '
            'run: `pre-commit migrate-config` to automatically fix this.',
        ),
    ]


def test_no_warning_for_non_deprecated_stages(caplog):
    config_obj = sample_local_config()
    config_obj['hooks'][0]['stages'] = ['pre-commit', 'pre-push']

    cfgv.validate(config_obj, CONFIG_REPO_DICT)

    assert caplog.record_tuples == []


def test_warning_for_deprecated_default_stages(caplog):
    cfg = {'default_stages': ['commit', 'push'], 'repos': []}

    cfgv.validate(cfg, CONFIG_SCHEMA)

    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            'top-level `default_stages` uses deprecated stage names '
            '(commit, push) which will be removed in a future version.  '
            'run: `pre-commit migrate-config` to automatically fix this.',
        ),
    ]


def test_no_warning_for_non_deprecated_default_stages(caplog):
    cfg = {'default_stages': ['pre-commit', 'pre-push'], 'repos': []}

    cfgv.validate(cfg, CONFIG_SCHEMA)

    assert caplog.record_tuples == []


def test_unsupported_language_migration():
    cfg = {'repos': [sample_local_config(), sample_local_config()]}
    cfg['repos'][0]['hooks'][0]['language'] = 'system'
    cfg['repos'][1]['hooks'][0]['language'] = 'script'

    cfgv.validate(cfg, CONFIG_SCHEMA)
    ret = cfgv.apply_defaults(cfg, CONFIG_SCHEMA)

    assert ret['repos'][0]['hooks'][0]['language'] == 'unsupported'
    assert ret['repos'][1]['hooks'][0]['language'] == 'unsupported_script'


def test_unsupported_language_migration_language_required():
    cfg = {'repos': [sample_local_config()]}
    del cfg['repos'][0]['hooks'][0]['language']

    with pytest.raises(cfgv.ValidationError):
        cfgv.validate(cfg, CONFIG_SCHEMA)


@pytest.mark.parametrize(
    'manifest_obj',
    (
        [{
            'id': 'a',
            'name': 'b',
            'entry': 'c',
            'language': 'python',
            'files': r'\.py$',
        }],
        [{
            'id': 'a',
            'name': 'b',
            'entry': 'c',
            'language': 'python',
            'language_version': 'python3.4',
            'files': r'\.py$',
        }],
        # A regression in 0.13.5: always_run and files are permissible
        [{
            'id': 'a',
            'name': 'b',
            'entry': 'c',
            'language': 'python',
            'files': '',
            'always_run': True,
        }],
    ),
)
def test_valid_manifests(manifest_obj):
    assert is_valid_according_to_schema(manifest_obj, MANIFEST_SCHEMA)


@pytest.mark.parametrize(
    'config_repo',
    (
        # i-dont-exist isn't a valid hook
        {'repo': 'meta', 'hooks': [{'id': 'i-dont-exist'}]},
        # invalid to set a language for a meta hook
        {'repo': 'meta', 'hooks': [{'id': 'identity', 'language': 'python'}]},
        # name override must be string
        {'repo': 'meta', 'hooks': [{'id': 'identity', 'name': False}]},
        pytest.param(
            {
                'repo': 'meta',
                'hooks': [{'id': 'identity', 'entry': 'echo hi'}],
            },
            id='cannot override entry for meta hooks',
        ),
    ),
)
def test_meta_hook_invalid(config_repo):
    with pytest.raises(cfgv.ValidationError):
        cfgv.validate(config_repo, CONFIG_REPO_DICT)


def test_meta_check_hooks_apply_only_at_top_level():
    cfg = {'id': 'check-hooks-apply'}
    cfg = cfgv.apply_defaults(cfg, META_HOOK_DICT)

    files_re = re.compile(cfg['files'])
    assert files_re.search('.pre-commit-config.yaml')
    assert not files_re.search('foo/.pre-commit-config.yaml')


@pytest.mark.parametrize(
    'mapping',
    (
        # invalid language key
        {'pony': '1.0'},
        # not a string for version
        {'python': 3},
    ),
)
def test_default_language_version_invalid(mapping):
    with pytest.raises(cfgv.ValidationError):
        cfgv.validate(mapping, DEFAULT_LANGUAGE_VERSION)


def test_parse_version():
    assert parse_version('0.0') == parse_version('0.0')
    assert parse_version('0.1') > parse_version('0.0')
    assert parse_version('2.1') >= parse_version('2')


def test_minimum_pre_commit_version_failing():
    cfg = {'repos': [], 'minimum_pre_commit_version': '999'}
    with pytest.raises(cfgv.ValidationError) as excinfo:
        cfgv.validate(cfg, CONFIG_SCHEMA)
    assert str(excinfo.value) == (
        f'\n'
        f'==> At Config()\n'
        f'==> At key: minimum_pre_commit_version\n'
        f'=====> pre-commit version 999 is required but version {C.VERSION} '
        f'is installed.  Perhaps run `pip install --upgrade pre-commit`.'
    )


def test_minimum_pre_commit_version_failing_in_config():
    cfg = {'repos': [sample_local_config()]}
    cfg['repos'][0]['hooks'][0]['minimum_pre_commit_version'] = '999'
    with pytest.raises(cfgv.ValidationError) as excinfo:
        cfgv.validate(cfg, CONFIG_SCHEMA)
    assert str(excinfo.value) == (
        f'\n'
        f'==> At Config()\n'
        f'==> At key: repos\n'
        f"==> At Repository(repo='local')\n"
        f'==> At key: hooks\n'
        f"==> At Hook(id='do_not_commit')\n"
        f'==> At key: minimum_pre_commit_version\n'
        f'=====> pre-commit version 999 is required but version {C.VERSION} '
        f'is installed.  Perhaps run `pip install --upgrade pre-commit`.'
    )


def test_minimum_pre_commit_version_failing_before_other_error():
    cfg = {'repos': 5, 'minimum_pre_commit_version': '999'}
    with pytest.raises(cfgv.ValidationError) as excinfo:
        cfgv.validate(cfg, CONFIG_SCHEMA)
    assert str(excinfo.value) == (
        f'\n'
        f'==> At Config()\n'
        f'==> At key: minimum_pre_commit_version\n'
        f'=====> pre-commit version 999 is required but version {C.VERSION} '
        f'is installed.  Perhaps run `pip install --upgrade pre-commit`.'
    )


def test_minimum_pre_commit_version_passing():
    cfg = {'repos': [], 'minimum_pre_commit_version': '0'}
    cfgv.validate(cfg, CONFIG_SCHEMA)


@pytest.mark.parametrize('schema', (CONFIG_SCHEMA, CONFIG_REPO_DICT))
def test_warn_additional(schema):
    allowed_keys = {item.key for item in schema.items if hasattr(item, 'key')}
    warn_additional, = (
        x for x in schema.items if isinstance(x, cfgv.WarnAdditionalKeys)
    )
    assert allowed_keys == set(warn_additional.keys)


def test_stages_migration_for_default_stages():
    cfg = {
        'default_stages': ['commit-msg', 'push', 'commit', 'merge-commit'],
        'repos': [],
    }
    cfgv.validate(cfg, CONFIG_SCHEMA)
    cfg = cfgv.apply_defaults(cfg, CONFIG_SCHEMA)
    assert cfg['default_stages'] == [
        'commit-msg', 'pre-push', 'pre-commit', 'pre-merge-commit',
    ]


def test_manifest_stages_defaulting():
    dct = {
        'id': 'fake-hook',
        'name': 'fake-hook',
        'entry': 'fake-hook',
        'language': 'system',
        'stages': ['commit-msg', 'push', 'commit', 'merge-commit'],
    }
    cfgv.validate(dct, MANIFEST_HOOK_DICT)
    dct = cfgv.apply_defaults(dct, MANIFEST_HOOK_DICT)
    assert dct['stages'] == [
        'commit-msg', 'pre-push', 'pre-commit', 'pre-merge-commit',
    ]


def test_config_hook_stages_defaulting_missing():
    dct = {'id': 'fake-hook'}
    cfgv.validate(dct, CONFIG_HOOK_DICT)
    dct = cfgv.apply_defaults(dct, CONFIG_HOOK_DICT)
    assert dct == {'id': 'fake-hook'}


def test_config_hook_stages_defaulting():
    dct = {
        'id': 'fake-hook',
        'stages': ['commit-msg', 'push', 'commit', 'merge-commit'],
    }
    cfgv.validate(dct, CONFIG_HOOK_DICT)
    dct = cfgv.apply_defaults(dct, CONFIG_HOOK_DICT)
    assert dct == {
        'id': 'fake-hook',
        'stages': ['commit-msg', 'pre-push', 'pre-commit', 'pre-merge-commit'],
    }


def test_manifest_v5_forward_compat(tmp_path):
    manifest = tmp_path.joinpath('.pre-commit-hooks.yaml')
    manifest.write_text('hooks: {}')

    with pytest.raises(InvalidManifestError) as excinfo:
        load_manifest(manifest)
    assert str(excinfo.value) == (
        f'\n'
        f'==> File {manifest}\n'
        f'=====> \n'
        f'=====> pre-commit version 5 is required but version {C.VERSION} '
        f'is installed.  Perhaps run `pip install --upgrade pre-commit`.'
    )
