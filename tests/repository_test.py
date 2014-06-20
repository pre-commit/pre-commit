from __future__ import absolute_import
from __future__ import unicode_literals

import io
import mock
import os.path
import pytest
from plumbum import local

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.repository import Repository
from testing.fixtures import git_dir
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.util import skipif_slowtests_false


def _test_hook_repo(
        tmpdir_factory,
        store,
        repo_path,
        hook_id,
        args,
        expected,
        expected_return_code=0,
):
    path = make_repo(tmpdir_factory, repo_path)
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    ret = repo.run_hook(hook_id, args)
    assert ret[0] == expected_return_code
    assert ret[1] == expected


@pytest.mark.integration
def test_python_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'python_hooks_repo',
        'foo', ['/dev/null'], "['/dev/null']\nHello World\n",
    )


@pytest.mark.integration
def test_versioned_python_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'python3_hooks_repo',
        'python3-hook', ['/dev/null'], "3.3\n['/dev/null']\nHello World\n",
    )


@skipif_slowtests_false
@pytest.mark.integration
def test_run_a_node_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'node_hooks_repo',
        'foo', [], 'Hello World\n',
    )


@skipif_slowtests_false
@pytest.mark.integration
def test_run_versioned_node_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'node_0_11_8_hooks_repo',
        'node-11-8-hook', ['/dev/null'], 'v0.11.8\nHello World\n',
    )


@skipif_slowtests_false
@pytest.mark.integration
def test_run_a_ruby_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'ruby_hooks_repo',
        'ruby_hook', [], 'Hello world from a ruby hook\n',
    )


@skipif_slowtests_false
@pytest.mark.integration
def test_run_versioned_ruby_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'ruby_1_9_3_hooks_repo',
        'ruby_hook', [], '1.9.3\n484\nHello world from a ruby hook\n',
    )


@pytest.mark.integration
def test_system_hook_with_spaces(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'system_hook_with_spaces_repo',
        'system-hook-with-spaces', [], 'Hello World\n',
    )


@pytest.mark.integration
def test_run_a_script_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'script_hooks_repo',
        'bash_hook', ['bar'], 'bar\nHello World\n',
    )


@pytest.mark.integration
def test_run_hook_with_spaced_args(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'arg_per_line_hooks_repo',
        'arg-per-line', ['foo bar', 'baz'], 'arg: foo bar\narg: baz\n',
    )


@pytest.mark.integration
def test_pcre_hook_no_match(tmpdir_factory, store):
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        with io.open('herp', 'w') as herp:
            herp.write('foo')

        with io.open('derp', 'w') as derp:
            derp.write('bar')

        _test_hook_repo(
            tmpdir_factory, store, 'pcre_hooks_repo',
            'regex-with-quotes', ['herp', 'derp'], '',
        )

        _test_hook_repo(
            tmpdir_factory, store, 'pcre_hooks_repo',
            'other-regex', ['herp', 'derp'], '',
        )


@pytest.mark.integration
def test_pcre_hook_matching(tmpdir_factory, store):
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        with io.open('herp', 'w') as herp:
            herp.write("\nherpfoo'bard\n")

        with io.open('derp', 'w') as derp:
            derp.write('[INFO] information yo\n')

        _test_hook_repo(
            tmpdir_factory, store, 'pcre_hooks_repo',
            'regex-with-quotes', ['herp', 'derp'], "herp:2:herpfoo'bard\n",
            expected_return_code=123,
        )

        _test_hook_repo(
            tmpdir_factory, store, 'pcre_hooks_repo',
            'other-regex', ['herp', 'derp'], 'derp:1:[INFO] information yo\n',
            expected_return_code=123,
        )


@pytest.mark.integration
def test_pcre_many_files(tmpdir_factory, store):
    # This is intended to simulate lots of passing files and one failing file
    # to make sure it still fails.  This is not the case when naively using
    # a system hook with `grep -H -n '...'` and expected_return_code=123.
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        with io.open('herp', 'w') as herp:
            herp.write('[INFO] info\n')

        _test_hook_repo(
            tmpdir_factory, store, 'pcre_hooks_repo',
            'other-regex',
            ['/dev/null'] * 15000 + ['herp'],
            'herp:1:[INFO] info\n',
            expected_return_code=123,
        )


@pytest.mark.integration
def test_cwd_of_hook(tmpdir_factory, store):
    # Note: this doubles as a test for `system` hooks
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        _test_hook_repo(
            tmpdir_factory, store, 'prints_cwd_repo',
            'prints_cwd', [], path + '\n',
        )


@pytest.mark.integration
def test_lots_of_files(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'script_hooks_repo',
        'bash_hook', ['/dev/null'] * 15000, mock.ANY,
    )


@pytest.fixture
def mock_repo_config():
    config = {
        'repo': 'git@github.com:pre-commit/pre-commit-hooks',
        'sha': '5e713f8878b7d100c0e059f8cc34be4fc2e8f897',
        'hooks': [{
            'id': 'pyflakes',
            'files': '\\.py$',
        }],
    }
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    return config_wrapped[0]


def test_repo_url(mock_repo_config):
    repo = Repository(mock_repo_config, None)
    assert repo.repo_url == 'git@github.com:pre-commit/pre-commit-hooks'


def test_sha(mock_repo_config):
    repo = Repository(mock_repo_config, None)
    assert repo.sha == '5e713f8878b7d100c0e059f8cc34be4fc2e8f897'


@pytest.mark.integration
def test_languages(tmpdir_factory, store):
    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    assert repo.languages == set([('python', 'default')])


def test_reinstall(tmpdir_factory, store):
    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    repo.require_installed()
    # Reinstall with same repo should not trigger another install
    # TODO: how to assert this?
    repo.require_installed()
    # Reinstall on another run should not trigger another install
    # TODO: how to assert this?
    repo = Repository.create(config, store)
    repo.require_installed()


@pytest.mark.integration
def test_really_long_file_paths(tmpdir_factory, store):
    base_path = tmpdir_factory.get()
    really_long_path = os.path.join(base_path, 'really_long' * 10)
    local['git']('init', really_long_path)

    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)

    with local.cwd(really_long_path):
        repo = Repository.create(config, store)
        repo.require_installed()


@pytest.mark.integration
def test_config_overrides_repo_specifics(tmpdir_factory, store):
    path = make_repo(tmpdir_factory, 'script_hooks_repo')
    config = make_config_from_repo(path)

    repo = Repository.create(config, store)
    assert repo.hooks['bash_hook']['files'] == ''
    # Set the file regex to something else
    config['hooks'][0]['files'] = '\\.sh$'
    repo = Repository.create(config, store)
    assert repo.hooks['bash_hook']['files'] == '\\.sh$'


def _create_repo_with_tags(tmpdir_factory, src, tag):
    path = make_repo(tmpdir_factory, src)
    with local.cwd(path):
        local['git']('tag', tag)
    return path


@pytest.mark.integration
def test_tags_on_repositories(in_tmpdir, tmpdir_factory, store):
    tag = 'v1.1'
    git_dir_1 = _create_repo_with_tags(tmpdir_factory, 'prints_cwd_repo', tag)
    git_dir_2 = _create_repo_with_tags(
        tmpdir_factory, 'script_hooks_repo', tag,
    )

    repo_1 = Repository.create(
        make_config_from_repo(git_dir_1, sha=tag), store,
    )
    ret = repo_1.run_hook('prints_cwd', [])
    assert ret[0] == 0
    assert ret[1].strip() == in_tmpdir

    repo_2 = Repository.create(
        make_config_from_repo(git_dir_2, sha=tag), store,
    )
    ret = repo_2.run_hook('bash_hook', ['bar'])
    assert ret[0] == 0
    assert ret[1] == 'bar\nHello World\n'
