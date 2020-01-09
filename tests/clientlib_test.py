import logging

import cfgv
import pytest

import pre_commit.constants as C
from pre_commit.clientlib import check_type_tag
from pre_commit.clientlib import CONFIG_HOOK_DICT
from pre_commit.clientlib import CONFIG_REPO_DICT
from pre_commit.clientlib import CONFIG_SCHEMA
from pre_commit.clientlib import DEFAULT_LANGUAGE_VERSION
from pre_commit.clientlib import MANIFEST_SCHEMA
from pre_commit.clientlib import MigrateShaToRev
from pre_commit.clientlib import validate_config_main
from pre_commit.clientlib import validate_manifest_main
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


@pytest.mark.parametrize(
    ('config_obj', 'expected'), (
        (
            {
                'repos': [{
                    'repo': 'git@github.com:pre-commit/pre-commit-hooks',
                    'rev': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
                    'hooks': [{'id': 'pyflakes', 'files': '\\.py$'}],
                }],
            },
            True,
        ),
        (
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
            True,
        ),
        (
            {
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
            },
            False,
        ),
    ),
)
def test_config_valid(config_obj, expected):
    ret = is_valid_according_to_schema(config_obj, CONFIG_SCHEMA)
    assert ret is expected


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


def test_validate_manifest_main_ok():
    assert not validate_manifest_main(('.pre-commit-hooks.yaml',))


def test_validate_config_main_ok():
    assert not validate_config_main(('.pre-commit-config.yaml',))


def test_validate_config_old_list_format_ok(tmpdir):
    f = tmpdir.join('cfg.yaml')
    f.write('-  {repo: meta, hooks: [{id: identity}]}')
    assert not validate_config_main((f.strpath,))


def test_validate_warn_on_unknown_keys_at_repo_level(tmpdir, caplog):
    f = tmpdir.join('cfg.yaml')
    f.write(
        '-   repo: https://gitlab.com/pycqa/flake8\n'
        '    rev: 3.7.7\n'
        '    hooks:\n'
        '    -   id: flake8\n'
        '    args: [--some-args]\n',
    )
    ret_val = validate_config_main((f.strpath,))
    assert not ret_val
    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            'Unexpected key(s) present on https://gitlab.com/pycqa/flake8: '
            'args',
        ),
    ]


def test_validate_warn_on_unknown_keys_at_top_level(tmpdir, caplog):
    f = tmpdir.join('cfg.yaml')
    f.write(
        'repos:\n'
        '-   repo: https://gitlab.com/pycqa/flake8\n'
        '    rev: 3.7.7\n'
        '    hooks:\n'
        '    -   id: flake8\n'
        'foo:\n'
        '    id: 1.0.0\n',
    )
    ret_val = validate_config_main((f.strpath,))
    assert not ret_val
    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            'Unexpected key(s) present at root: foo',
        ),
    ]


@pytest.mark.parametrize('fn', (validate_config_main, validate_manifest_main))
def test_mains_not_ok(tmpdir, fn):
    not_yaml = tmpdir.join('f.notyaml')
    not_yaml.write('{')
    not_schema = tmpdir.join('notconfig.yaml')
    not_schema.write('{}')

    assert fn(('does-not-exist',))
    assert fn((not_yaml.strpath,))
    assert fn((not_schema.strpath,))


@pytest.mark.parametrize(
    ('manifest_obj', 'expected'),
    (
        (
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'files': r'\.py$',
            }],
            True,
        ),
        (
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'language_version': 'python3.4',
                'files': r'\.py$',
            }],
            True,
        ),
        (
            # A regression in 0.13.5: always_run and files are permissible
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'files': '',
                'always_run': True,
            }],
            True,
        ),
    ),
)
def test_valid_manifests(manifest_obj, expected):
    ret = is_valid_according_to_schema(manifest_obj, MANIFEST_SCHEMA)
    assert ret is expected


@pytest.mark.parametrize(
    'dct',
    (
        {'repo': 'local'}, {'repo': 'meta'},
        {'repo': 'wat', 'sha': 'wat'}, {'repo': 'wat', 'rev': 'wat'},
    ),
)
def test_migrate_sha_to_rev_ok(dct):
    MigrateShaToRev().check(dct)


def test_migrate_sha_to_rev_dont_specify_both():
    with pytest.raises(cfgv.ValidationError) as excinfo:
        MigrateShaToRev().check({'repo': 'a', 'sha': 'b', 'rev': 'c'})
    msg, = excinfo.value.args
    assert msg == 'Cannot specify both sha and rev'


@pytest.mark.parametrize(
    'dct',
    (
        {'repo': 'a'},
        {'repo': 'meta', 'sha': 'a'}, {'repo': 'meta', 'rev': 'a'},
    ),
)
def test_migrate_sha_to_rev_conditional_check_failures(dct):
    with pytest.raises(cfgv.ValidationError):
        MigrateShaToRev().check(dct)


def test_migrate_to_sha_apply_default():
    dct = {'repo': 'a', 'sha': 'b'}
    MigrateShaToRev().apply_default(dct)
    assert dct == {'repo': 'a', 'rev': 'b'}


def test_migrate_to_sha_ok():
    dct = {'repo': 'a', 'rev': 'b'}
    MigrateShaToRev().apply_default(dct)
    assert dct == {'repo': 'a', 'rev': 'b'}


@pytest.mark.parametrize(
    'config_repo',
    (
        # i-dont-exist isn't a valid hook
        {'repo': 'meta', 'hooks': [{'id': 'i-dont-exist'}]},
        # invalid to set a language for a meta hook
        {'repo': 'meta', 'hooks': [{'id': 'identity', 'language': 'python'}]},
        # name override must be string
        {'repo': 'meta', 'hooks': [{'id': 'identity', 'name': False}]},
    ),
)
def test_meta_hook_invalid(config_repo):
    with pytest.raises(cfgv.ValidationError):
        cfgv.validate(config_repo, CONFIG_REPO_DICT)


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


def test_minimum_pre_commit_version_failing():
    with pytest.raises(cfgv.ValidationError) as excinfo:
        cfg = {'repos': [], 'minimum_pre_commit_version': '999'}
        cfgv.validate(cfg, CONFIG_SCHEMA)
    assert str(excinfo.value) == (
        '\n'
        '==> At Config()\n'
        '==> At key: minimum_pre_commit_version\n'
        '=====> pre-commit version 999 is required but version {} is '
        'installed.  Perhaps run `pip install --upgrade pre-commit`.'.format(
            C.VERSION,
        )
    )


def test_minimum_pre_commit_version_passing():
    cfg = {'repos': [], 'minimum_pre_commit_version': '0'}
    cfgv.validate(cfg, CONFIG_SCHEMA)


@pytest.mark.parametrize('schema', (CONFIG_SCHEMA, CONFIG_REPO_DICT))
def test_warn_additional(schema):
    allowed_keys = {item.key for item in schema.items if hasattr(item, 'key')}
    warn_additional, = [
        x for x in schema.items if isinstance(x, cfgv.WarnAdditionalKeys)
    ]
    assert allowed_keys == set(warn_additional.keys)
