from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os.path
import shutil

import mock
import pytest

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.languages.python import PythonEnv
from pre_commit.ordereddict import OrderedDict
from pre_commit.repository import Repository
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.fixtures import git_dir
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.util import skipif_slowtests_false
from testing.util import xfailif_no_pcre_support
from testing.util import xfailif_windows_no_node
from testing.util import xfailif_windows_no_ruby


def _test_hook_repo(
        tmpdir_factory,
        store,
        repo_path,
        hook_id,
        args,
        expected,
        expected_return_code=0,
        config_kwargs=None
):
    path = make_repo(tmpdir_factory, repo_path)
    config = make_config_from_repo(path, **(config_kwargs or {}))
    repo = Repository.create(config, store)
    hook_dict = [
        hook for repo_hook_id, hook in repo.hooks if repo_hook_id == hook_id
    ][0]
    ret = repo.run_hook(hook_dict, args)
    assert ret[0] == expected_return_code
    assert ret[1].replace('\r\n', '\n') == expected


@pytest.mark.integration
def test_python_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'python_hooks_repo',
        'foo', [os.devnull], "['{0}']\nHello World\n".format(os.devnull),
    )


@pytest.mark.integration
def test_python_hook_args_with_spaces(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'python_hooks_repo',
        'foo',
        [],
        "['i have spaces', 'and\"\\'quotes', '$and !this']\n"
        'Hello World\n',
        config_kwargs={
            'hooks': [{
                'id': 'foo',
                'args': ['i have spaces', 'and"\'quotes', '$and !this'],
            }]
        },
    )


@pytest.mark.integration
def test_switch_language_versions_doesnt_clobber(tmpdir_factory, store):
    # We're using the python3 repo because it prints the python version
    path = make_repo(tmpdir_factory, 'python3_hooks_repo')

    def run_on_version(version, expected_output):
        config = make_config_from_repo(
            path, hooks=[{'id': 'python3-hook', 'language_version': version}],
        )
        repo = Repository.create(config, store)
        hook_dict, = [
            hook
            for repo_hook_id, hook in repo.hooks
            if repo_hook_id == 'python3-hook'
        ]
        ret = repo.run_hook(hook_dict, [])
        assert ret[0] == 0
        assert ret[1].replace('\r\n', '\n') == expected_output

    run_on_version('python3.4', '3.4\n[]\nHello World\n')
    run_on_version('python3.3', '3.3\n[]\nHello World\n')


@pytest.mark.integration
def test_versioned_python_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'python3_hooks_repo',
        'python3-hook',
        [os.devnull],
        "3.3\n['{0}']\nHello World\n".format(os.devnull),
    )


@skipif_slowtests_false
@xfailif_windows_no_node
@pytest.mark.integration
def test_run_a_node_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'node_hooks_repo',
        'foo', ['/dev/null'], 'Hello World\n',
    )


@skipif_slowtests_false
@xfailif_windows_no_node
@pytest.mark.integration
def test_run_versioned_node_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'node_0_11_8_hooks_repo',
        'node-11-8-hook', ['/dev/null'], 'v0.11.8\nHello World\n',
    )


@skipif_slowtests_false
@xfailif_windows_no_ruby
@pytest.mark.integration
def test_run_a_ruby_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'ruby_hooks_repo',
        'ruby_hook', ['/dev/null'], 'Hello world from a ruby hook\n',
    )


@skipif_slowtests_false
@xfailif_windows_no_ruby
@pytest.mark.integration
def test_run_versioned_ruby_hook(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'ruby_1_9_3_hooks_repo',
        'ruby_hook',
        ['/dev/null'],
        '1.9.3\n484\nHello world from a ruby hook\n',
    )


@pytest.mark.integration
def test_system_hook_with_spaces(tmpdir_factory, store):
    _test_hook_repo(
        tmpdir_factory, store, 'system_hook_with_spaces_repo',
        'system-hook-with-spaces', ['/dev/null'], 'Hello World\n',
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
        'arg-per-line',
        ['foo bar', 'baz'],
        'arg: hello\narg: world\narg: foo bar\narg: baz\n',
    )


@xfailif_no_pcre_support
@pytest.mark.integration
def test_pcre_hook_no_match(tmpdir_factory, store):
    path = git_dir(tmpdir_factory)
    with cwd(path):
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


@xfailif_no_pcre_support
@pytest.mark.integration
def test_pcre_hook_matching(tmpdir_factory, store):
    path = git_dir(tmpdir_factory)
    with cwd(path):
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


@xfailif_no_pcre_support
@pytest.mark.integration
def test_pcre_many_files(tmpdir_factory, store):
    # This is intended to simulate lots of passing files and one failing file
    # to make sure it still fails.  This is not the case when naively using
    # a system hook with `grep -H -n '...'` and expected_return_code=123.
    path = git_dir(tmpdir_factory)
    with cwd(path):
        with io.open('herp', 'w') as herp:
            herp.write('[INFO] info\n')

        _test_hook_repo(
            tmpdir_factory, store, 'pcre_hooks_repo',
            'other-regex',
            ['/dev/null'] * 15000 + ['herp'],
            'herp:1:[INFO] info\n',
            expected_return_code=123,
        )


def _norm_pwd(path):
    # Under windows bash's temp and windows temp is different.
    # This normalizes to the bash /tmp
    return cmd_output(
        'bash', '-c', "cd '{0}' && pwd".format(path),
    )[1].strip()


@pytest.mark.integration
def test_cwd_of_hook(tmpdir_factory, store):
    # Note: this doubles as a test for `system` hooks
    path = git_dir(tmpdir_factory)
    with cwd(path):
        _test_hook_repo(
            tmpdir_factory, store, 'prints_cwd_repo',
            'prints_cwd', ['-L'], _norm_pwd(path) + '\n',
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


def test_reinstall(tmpdir_factory, store, log_info_mock):
    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    repo.require_installed()
    # We print some logging during clone (1) + install (3)
    assert log_info_mock.call_count == 4
    log_info_mock.reset_mock()
    # Reinstall with same repo should not trigger another install
    repo.require_installed()
    assert log_info_mock.call_count == 0
    # Reinstall on another run should not trigger another install
    repo = Repository.create(config, store)
    repo.require_installed()
    assert log_info_mock.call_count == 0


def test_control_c_control_c_on_install(tmpdir_factory, store):
    """Regression test for #186."""
    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    hook = repo.hooks[0][1]

    class MyKeyboardInterrupt(KeyboardInterrupt):
        pass

    # To simulate a killed install, we'll make PythonEnv.run raise ^C
    # and then to simulate a second ^C during cleanup, we'll make shutil.rmtree
    # raise as well.
    with pytest.raises(MyKeyboardInterrupt):
        with mock.patch.object(
            PythonEnv, 'run', side_effect=MyKeyboardInterrupt,
        ):
            with mock.patch.object(
                shutil, 'rmtree', side_effect=MyKeyboardInterrupt,
            ):
                repo.run_hook(hook, [])

    # Should have made an environment, however this environment is broken!
    assert os.path.exists(repo.cmd_runner.path('py_env-default'))

    # However, it should be perfectly runnable (reinstall after botched
    # install)
    retv, stdout, stderr = repo.run_hook(hook, [])
    assert retv == 0


@pytest.mark.integration
def test_really_long_file_paths(tmpdir_factory, store):
    base_path = tmpdir_factory.get()
    really_long_path = os.path.join(base_path, 'really_long' * 10)
    cmd_output('git', 'init', really_long_path)

    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)

    with cwd(really_long_path):
        repo = Repository.create(config, store)
        repo.require_installed()


@pytest.mark.integration
def test_config_overrides_repo_specifics(tmpdir_factory, store):
    path = make_repo(tmpdir_factory, 'script_hooks_repo')
    config = make_config_from_repo(path)

    repo = Repository.create(config, store)
    assert repo.hooks[0][1]['files'] == ''
    # Set the file regex to something else
    config['hooks'][0]['files'] = '\\.sh$'
    repo = Repository.create(config, store)
    assert repo.hooks[0][1]['files'] == '\\.sh$'


def _create_repo_with_tags(tmpdir_factory, src, tag):
    path = make_repo(tmpdir_factory, src)
    with cwd(path):
        cmd_output('git', 'tag', tag)
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
    ret = repo_1.run_hook(repo_1.hooks[0][1], ['-L'])
    assert ret[0] == 0
    assert ret[1].strip() == _norm_pwd(in_tmpdir)

    repo_2 = Repository.create(
        make_config_from_repo(git_dir_2, sha=tag), store,
    )
    ret = repo_2.run_hook(repo_2.hooks[0][1], ['bar'])
    assert ret[0] == 0
    assert ret[1] == 'bar\nHello World\n'


def test_local_repository():
    config = OrderedDict((
        ('repo', 'local'),
        ('hooks', [OrderedDict((
            ('id', 'do_not_commit'),
            ('name', 'Block if "DO NOT COMMIT" is found'),
            ('entry', 'DO NOT COMMIT'),
            ('language', 'pcre'),
            ('files', '^(.*)$'),
        ))])
    ))
    local_repo = Repository.create(config, 'dummy')
    with pytest.raises(NotImplementedError):
        local_repo.sha
    with pytest.raises(NotImplementedError):
        local_repo.manifest
    assert len(local_repo.hooks) == 1
