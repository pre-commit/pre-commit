from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import io
import os.path
import re
import shutil

import mock
import pytest

import pre_commit.constants as C
from pre_commit import five
from pre_commit import parse_shebang
from pre_commit.clientlib import load_manifest
from pre_commit.languages import golang
from pre_commit.languages import helpers
from pre_commit.languages import node
from pre_commit.languages import pcre
from pre_commit.languages import python
from pre_commit.languages import ruby
from pre_commit.repository import Repository
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.fixtures import config_with_local_hooks
from testing.fixtures import git_dir
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.fixtures import modify_manifest
from testing.util import get_resource_path
from testing.util import skipif_cant_run_docker
from testing.util import skipif_cant_run_swift
from testing.util import xfailif_no_pcre_support
from testing.util import xfailif_windows_no_node
from testing.util import xfailif_windows_no_ruby


def _norm_out(b):
    return b.replace(b'\r\n', b'\n')


def _test_hook_repo(
        tempdir_factory,
        store,
        repo_path,
        hook_id,
        args,
        expected,
        expected_return_code=0,
        config_kwargs=None,
):
    path = make_repo(tempdir_factory, repo_path)
    config = make_config_from_repo(path, **(config_kwargs or {}))
    repo = Repository.create(config, store)
    hook_dict, = [
        hook for repo_hook_id, hook in repo.hooks if repo_hook_id == hook_id
    ]
    ret = repo.run_hook(hook_dict, args)
    assert ret[0] == expected_return_code
    assert _norm_out(ret[1]) == expected


@pytest.mark.integration
def test_python_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'python_hooks_repo',
        'foo', [os.devnull],
        b"['" + five.to_bytes(os.devnull) + b"']\nHello World\n",
    )


@pytest.mark.integration
def test_python_hook_default_version(tempdir_factory, store):
    # make sure that this continues to work for platforms where default
    # language detection does not work
    with mock.patch.object(
            python, 'get_default_version', return_value='default',
    ):
        test_python_hook(tempdir_factory, store)


@pytest.mark.integration
def test_python_hook_args_with_spaces(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'python_hooks_repo',
        'foo',
        [],
        b"['i have spaces', 'and\"\\'quotes', '$and !this']\n"
        b'Hello World\n',
        config_kwargs={
            'hooks': [{
                'id': 'foo',
                'args': ['i have spaces', 'and"\'quotes', '$and !this'],
            }],
        },
    )


@pytest.mark.integration
def test_python_hook_weird_setup_cfg(tempdir_factory, store):
    path = git_dir(tempdir_factory)
    with cwd(path):
        with io.open('setup.cfg', 'w') as setup_cfg:
            setup_cfg.write('[install]\ninstall_scripts=/usr/sbin\n')

        _test_hook_repo(
            tempdir_factory, store, 'python_hooks_repo',
            'foo', [os.devnull],
            b"['" + five.to_bytes(os.devnull) + b"']\nHello World\n",
        )


@pytest.mark.integration
def test_switch_language_versions_doesnt_clobber(tempdir_factory, store):
    # We're using the python3 repo because it prints the python version
    path = make_repo(tempdir_factory, 'python3_hooks_repo')

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
        assert _norm_out(ret[1]) == expected_output

    run_on_version('python2', b'2\n[]\nHello World\n')
    run_on_version('python3', b'3\n[]\nHello World\n')


@pytest.mark.integration
def test_versioned_python_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'python3_hooks_repo',
        'python3-hook',
        [os.devnull],
        b"3\n['" + five.to_bytes(os.devnull) + b"']\nHello World\n",
    )


@skipif_cant_run_docker
@pytest.mark.integration
def test_run_a_docker_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'docker_hooks_repo',
        'docker-hook',
        ['Hello World from docker'], b'Hello World from docker\n',
    )


@skipif_cant_run_docker
@pytest.mark.integration
def test_run_a_docker_hook_with_entry_args(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'docker_hooks_repo',
        'docker-hook-arg',
        ['Hello World from docker'], b'Hello World from docker',
    )


@skipif_cant_run_docker
@pytest.mark.integration
def test_run_a_failing_docker_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'docker_hooks_repo',
        'docker-hook-failing',
        ['Hello World from docker'], b'',
        expected_return_code=1,
    )


@skipif_cant_run_docker
@pytest.mark.integration
@pytest.mark.parametrize('hook_id', ('echo-entrypoint', 'echo-cmd'))
def test_run_a_docker_image_hook(tempdir_factory, store, hook_id):
    _test_hook_repo(
        tempdir_factory, store, 'docker_image_hooks_repo',
        hook_id,
        ['Hello World from docker'], b'Hello World from docker\n',
    )


@xfailif_windows_no_node
@pytest.mark.integration
def test_run_a_node_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'node_hooks_repo',
        'foo', ['/dev/null'], b'Hello World\n',
    )


@xfailif_windows_no_node
@pytest.mark.integration
def test_run_versioned_node_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'node_0_11_8_hooks_repo',
        'node-11-8-hook', ['/dev/null'], b'v0.11.8\nHello World\n',
    )


@xfailif_windows_no_ruby
@pytest.mark.integration
def test_run_a_ruby_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'ruby_hooks_repo',
        'ruby_hook', ['/dev/null'], b'Hello world from a ruby hook\n',
    )


@xfailif_windows_no_ruby
@pytest.mark.integration
def test_run_versioned_ruby_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'ruby_versioned_hooks_repo',
        'ruby_hook',
        ['/dev/null'],
        b'2.1.5\nHello world from a ruby hook\n',
    )


@xfailif_windows_no_ruby
@pytest.mark.integration
def test_run_ruby_hook_with_disable_shared_gems(
        tempdir_factory,
        store,
        tmpdir,
):
    """Make sure a Gemfile in the project doesn't interfere."""
    tmpdir.join('Gemfile').write('gem "lol_hai"')
    tmpdir.join('.bundle').mkdir()
    tmpdir.join('.bundle', 'config').write(
        'BUNDLE_DISABLE_SHARED_GEMS: true\n'
        'BUNDLE_PATH: vendor/gem\n',
    )
    with cwd(tmpdir.strpath):
        _test_hook_repo(
            tempdir_factory, store, 'ruby_versioned_hooks_repo',
            'ruby_hook',
            ['/dev/null'],
            b'2.1.5\nHello world from a ruby hook\n',
        )


@pytest.mark.integration
def test_system_hook_with_spaces(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'system_hook_with_spaces_repo',
        'system-hook-with-spaces', ['/dev/null'], b'Hello World\n',
    )


@skipif_cant_run_swift
@pytest.mark.integration
def test_swift_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'swift_hooks_repo',
        'swift-hooks-repo', [], b'Hello, world!\n',
    )


@pytest.mark.integration
def test_golang_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'golang_hooks_repo',
        'golang-hook', [], b'hello world\n',
    )


@pytest.mark.integration
def test_missing_executable(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'not_found_exe',
        'not-found-exe', ['/dev/null'],
        b'Executable `i-dont-exist-lol` not found',
        expected_return_code=1,
    )


@pytest.mark.integration
def test_run_a_script_hook(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'script_hooks_repo',
        'bash_hook', ['bar'], b'bar\nHello World\n',
    )


@pytest.mark.integration
def test_run_hook_with_spaced_args(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'arg_per_line_hooks_repo',
        'arg-per-line',
        ['foo bar', 'baz'],
        b'arg: hello\narg: world\narg: foo bar\narg: baz\n',
    )


@pytest.mark.integration
def test_run_hook_with_curly_braced_arguments(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'arg_per_line_hooks_repo',
        'arg-per-line',
        [],
        b"arg: hi {1}\narg: I'm {a} problem\n",
        config_kwargs={
            'hooks': [{
                'id': 'arg-per-line',
                'args': ['hi {1}', "I'm {a} problem"],
            }],
        },
    )


def _make_grep_repo(language, entry, store, args=()):
    config = collections.OrderedDict((
        ('repo', 'local'),
        (
            'hooks', [
                collections.OrderedDict((
                    ('id', 'grep-hook'),
                    ('name', 'grep-hook'),
                    ('language', language),
                    ('entry', entry),
                    ('args', args),
                    ('types', ['text']),
                )),
            ],
        ),
    ))
    repo = Repository.create(config, store)
    (_, hook), = repo.hooks
    return repo, hook


@pytest.fixture
def greppable_files(tmpdir):
    with tmpdir.as_cwd():
        cmd_output('git', 'init', '.')
        tmpdir.join('f1').write_binary(b"hello'hi\nworld\n")
        tmpdir.join('f2').write_binary(b'foo\nbar\nbaz\n')
        tmpdir.join('f3').write_binary(b'[WARN] hi\n')
        yield tmpdir


class TestPygrep(object):
    language = 'pygrep'

    def test_grep_hook_matching(self, greppable_files, store):
        repo, hook = _make_grep_repo(self.language, 'ello', store)
        ret, out, _ = repo.run_hook(hook, ('f1', 'f2', 'f3'))
        assert ret == 1
        assert _norm_out(out) == b"f1:1:hello'hi\n"

    def test_grep_hook_case_insensitive(self, greppable_files, store):
        repo, hook = _make_grep_repo(self.language, 'ELLO', store, args=['-i'])
        ret, out, _ = repo.run_hook(hook, ('f1', 'f2', 'f3'))
        assert ret == 1
        assert _norm_out(out) == b"f1:1:hello'hi\n"

    @pytest.mark.parametrize('regex', ('nope', "foo'bar", r'^\[INFO\]'))
    def test_grep_hook_not_matching(self, regex, greppable_files, store):
        repo, hook = _make_grep_repo(self.language, regex, store)
        ret, out, _ = repo.run_hook(hook, ('f1', 'f2', 'f3'))
        assert (ret, out) == (0, b'')


@xfailif_no_pcre_support
class TestPCRE(TestPygrep):
    """organized as a class for xfailing pcre"""
    language = 'pcre'

    def test_pcre_hook_many_files(self, greppable_files, store):
        # This is intended to simulate lots of passing files and one failing
        # file to make sure it still fails.  This is not the case when naively
        # using a system hook with `grep -H -n '...'`
        repo, hook = _make_grep_repo('pcre', 'ello', store)
        ret, out, _ = repo.run_hook(hook, (os.devnull,) * 15000 + ('f1',))
        assert ret == 1
        assert _norm_out(out) == b"f1:1:hello'hi\n"

    def test_missing_pcre_support(self, greppable_files, store):
        orig_find_executable = parse_shebang.find_executable

        def no_grep(exe, **kwargs):
            if exe == pcre.GREP:
                return None
            else:
                return orig_find_executable(exe, **kwargs)

        with mock.patch.object(parse_shebang, 'find_executable', no_grep):
            repo, hook = _make_grep_repo('pcre', 'ello', store)
            ret, out, _ = repo.run_hook(hook, ('f1', 'f2', 'f3'))
            assert ret == 1
            expected = 'Executable `{}` not found'.format(pcre.GREP).encode()
            assert out == expected


def _norm_pwd(path):
    # Under windows bash's temp and windows temp is different.
    # This normalizes to the bash /tmp
    return cmd_output(
        'bash', '-c', "cd '{}' && pwd".format(path),
        encoding=None,
    )[1].strip()


@pytest.mark.integration
def test_cwd_of_hook(tempdir_factory, store):
    # Note: this doubles as a test for `system` hooks
    path = git_dir(tempdir_factory)
    with cwd(path):
        _test_hook_repo(
            tempdir_factory, store, 'prints_cwd_repo',
            'prints_cwd', ['-L'], _norm_pwd(path) + b'\n',
        )


@pytest.mark.integration
def test_lots_of_files(tempdir_factory, store):
    _test_hook_repo(
        tempdir_factory, store, 'script_hooks_repo',
        'bash_hook', ['/dev/null'] * 15000, mock.ANY,
    )


@pytest.mark.integration
def test_venvs(tempdir_factory, store):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    venv, = repo._venvs
    assert venv == (mock.ANY, 'python', python.get_default_version(), [])


@pytest.mark.integration
def test_additional_dependencies(tempdir_factory, store):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    config['hooks'][0]['additional_dependencies'] = ['pep8']
    repo = Repository.create(config, store)
    venv, = repo._venvs
    assert venv == (mock.ANY, 'python', python.get_default_version(), ['pep8'])


@pytest.mark.integration
def test_additional_dependencies_duplicated(
        tempdir_factory, store, log_warning_mock,
):
    path = make_repo(tempdir_factory, 'ruby_hooks_repo')
    config = make_config_from_repo(path)
    deps = ['thread_safe', 'tins', 'thread_safe']
    config['hooks'][0]['additional_dependencies'] = deps
    repo = Repository.create(config, store)
    venv, = repo._venvs
    assert venv == (mock.ANY, 'ruby', 'default', ['thread_safe', 'tins'])


@pytest.mark.integration
def test_additional_python_dependencies_installed(tempdir_factory, store):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    config['hooks'][0]['additional_dependencies'] = ['mccabe']
    repo = Repository.create(config, store)
    repo.require_installed()
    with python.in_env(repo._cmd_runner, 'default'):
        output = cmd_output('pip', 'freeze', '-l')[1]
        assert 'mccabe' in output


@pytest.mark.integration
def test_additional_dependencies_roll_forward(tempdir_factory, store):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    # Run the repo once without additional_dependencies
    repo = Repository.create(config, store)
    repo.require_installed()
    # Now run it with additional_dependencies
    config['hooks'][0]['additional_dependencies'] = ['mccabe']
    repo = Repository.create(config, store)
    repo.require_installed()
    # We should see our additional dependency installed
    with python.in_env(repo._cmd_runner, 'default'):
        output = cmd_output('pip', 'freeze', '-l')[1]
        assert 'mccabe' in output


@xfailif_windows_no_ruby
@pytest.mark.integration
def test_additional_ruby_dependencies_installed(
        tempdir_factory, store,
):  # pragma: no cover (non-windows)
    path = make_repo(tempdir_factory, 'ruby_hooks_repo')
    config = make_config_from_repo(path)
    config['hooks'][0]['additional_dependencies'] = ['thread_safe', 'tins']
    repo = Repository.create(config, store)
    repo.require_installed()
    with ruby.in_env(repo._cmd_runner, 'default'):
        output = cmd_output('gem', 'list', '--local')[1]
        assert 'thread_safe' in output
        assert 'tins' in output


@xfailif_windows_no_node
@pytest.mark.integration
def test_additional_node_dependencies_installed(
        tempdir_factory, store,
):  # pragma: no cover (non-windows)
    path = make_repo(tempdir_factory, 'node_hooks_repo')
    config = make_config_from_repo(path)
    # Careful to choose a small package that's not depped by npm
    config['hooks'][0]['additional_dependencies'] = ['lodash']
    repo = Repository.create(config, store)
    repo.require_installed()
    with node.in_env(repo._cmd_runner, 'default'):
        cmd_output('npm', 'config', 'set', 'global', 'true')
        output = cmd_output('npm', 'ls')[1]
        assert 'lodash' in output


@pytest.mark.integration
def test_additional_golang_dependencies_installed(
        tempdir_factory, store,
):
    path = make_repo(tempdir_factory, 'golang_hooks_repo')
    config = make_config_from_repo(path)
    # A small go package
    deps = ['github.com/golang/example/hello']
    config['hooks'][0]['additional_dependencies'] = deps
    repo = Repository.create(config, store)
    repo.require_installed()
    binaries = os.listdir(repo._cmd_runner.path(
        helpers.environment_dir(golang.ENVIRONMENT_DIR, 'default'), 'bin',
    ))
    # normalize for windows
    binaries = [os.path.splitext(binary)[0] for binary in binaries]
    assert 'hello' in binaries


def test_reinstall(tempdir_factory, store, log_info_mock):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
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


def test_control_c_control_c_on_install(tempdir_factory, store):
    """Regression test for #186."""
    path = make_repo(tempdir_factory, 'python_hooks_repo')
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
            helpers, 'run_setup_cmd', side_effect=MyKeyboardInterrupt,
        ):
            with mock.patch.object(
                shutil, 'rmtree', side_effect=MyKeyboardInterrupt,
            ):
                repo.run_hook(hook, [])

    # Should have made an environment, however this environment is broken!
    envdir = 'py_env-{}'.format(python.get_default_version())
    assert repo._cmd_runner.exists(envdir)

    # However, it should be perfectly runnable (reinstall after botched
    # install)
    retv, stdout, stderr = repo.run_hook(hook, [])
    assert retv == 0


def test_invalidated_virtualenv(tempdir_factory, store):
    # A cached virtualenv may become invalidated if the system python upgrades
    # This should not cause every hook in that virtualenv to fail.
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)

    # Simulate breaking of the virtualenv
    repo.require_installed()
    version = python.get_default_version()
    libdir = repo._cmd_runner.path('py_env-{}'.format(version), 'lib', version)
    paths = [
        os.path.join(libdir, p) for p in ('site.py', 'site.pyc', '__pycache__')
    ]
    cmd_output('rm', '-rf', *paths)

    # pre-commit should rebuild the virtualenv and it should be runnable
    repo = Repository.create(config, store)
    hook = repo.hooks[0][1]
    retv, stdout, stderr = repo.run_hook(hook, [])
    assert retv == 0


@pytest.mark.integration
def test_really_long_file_paths(tempdir_factory, store):
    base_path = tempdir_factory.get()
    really_long_path = os.path.join(base_path, 'really_long' * 10)
    cmd_output('git', 'init', really_long_path)

    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path)

    with cwd(really_long_path):
        repo = Repository.create(config, store)
        repo.require_installed()


@pytest.mark.integration
def test_config_overrides_repo_specifics(tempdir_factory, store):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    config = make_config_from_repo(path)

    repo = Repository.create(config, store)
    assert repo.hooks[0][1]['files'] == ''
    # Set the file regex to something else
    config['hooks'][0]['files'] = '\\.sh$'
    repo = Repository.create(config, store)
    assert repo.hooks[0][1]['files'] == '\\.sh$'


def _create_repo_with_tags(tempdir_factory, src, tag):
    path = make_repo(tempdir_factory, src)
    with cwd(path):
        cmd_output('git', 'tag', tag)
    return path


@pytest.mark.integration
def test_tags_on_repositories(in_tmpdir, tempdir_factory, store):
    tag = 'v1.1'
    git_dir_1 = _create_repo_with_tags(tempdir_factory, 'prints_cwd_repo', tag)
    git_dir_2 = _create_repo_with_tags(
        tempdir_factory, 'script_hooks_repo', tag,
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
    assert ret[1] == b'bar\nHello World\n'


def test_local_repository():
    config = config_with_local_hooks()
    local_repo = Repository.create(config, 'dummy')
    with pytest.raises(NotImplementedError):
        local_repo.manifest
    assert len(local_repo.hooks) == 1


def test_local_python_repo(store):
    # Make a "local" hooks repo that just installs our other hooks repo
    repo_path = get_resource_path('python_hooks_repo')
    manifest = load_manifest(os.path.join(repo_path, C.MANIFEST_FILE))
    hooks = [
        dict(hook, additional_dependencies=[repo_path]) for hook in manifest
    ]
    config = {'repo': 'local', 'hooks': hooks}
    repo = Repository.create(config, store)
    (_, hook), = repo.hooks
    # language_version should have been adjusted to the interpreter version
    assert hook['language_version'] != 'default'
    ret = repo.run_hook(hook, ('filename',))
    assert ret[0] == 0
    assert _norm_out(ret[1]) == b"['filename']\nHello World\n"


def test_hook_id_not_present(tempdir_factory, store, fake_log_handler):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    config = make_config_from_repo(path)
    config['hooks'][0]['id'] = 'i-dont-exist'
    repo = Repository.create(config, store)
    with pytest.raises(SystemExit):
        repo.require_installed()
    assert fake_log_handler.handle.call_args[0][0].msg == (
        '`i-dont-exist` is not present in repository file://{}.  '
        'Typo? Perhaps it is introduced in a newer version?  '
        'Often `pre-commit autoupdate` fixes this.'.format(path)
    )


def test_meta_hook_not_present(store, fake_log_handler):
    config = {'repo': 'meta', 'hooks': [{'id': 'i-dont-exist'}]}
    repo = Repository.create(config, store)
    with pytest.raises(SystemExit):
        repo.require_installed()
    assert fake_log_handler.handle.call_args[0][0].msg == (
        '`i-dont-exist` is not a valid meta hook.  '
        'Typo? Perhaps it is introduced in a newer version?  '
        'Often `pip install --upgrade pre-commit` fixes this.'
    )


def test_too_new_version(tempdir_factory, store, fake_log_handler):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    with modify_manifest(path) as manifest:
        manifest[0]['minimum_pre_commit_version'] = '999.0.0'
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)
    with pytest.raises(SystemExit):
        repo.require_installed()
    msg = fake_log_handler.handle.call_args[0][0].msg
    assert re.match(
        r'^The hook `bash_hook` requires pre-commit version 999\.0\.0 but '
        r'version \d+\.\d+\.\d+ is installed.  '
        r'Perhaps run `pip install --upgrade pre-commit`\.$',
        msg,
    )


@pytest.mark.parametrize('version', ('0.1.0', C.VERSION))
def test_versions_ok(tempdir_factory, store, version):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    with modify_manifest(path) as manifest:
        manifest[0]['minimum_pre_commit_version'] = version
    config = make_config_from_repo(path)
    # Should succeed
    Repository.create(config, store).require_installed()


def test_manifest_hooks(tempdir_factory, store):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    config = make_config_from_repo(path)
    repo = Repository.create(config, store)

    assert repo.manifest_hooks['bash_hook'] == {
        'always_run': False,
        'additional_dependencies': [],
        'args': [],
        'description': '',
        'entry': 'bin/hook.sh',
        'exclude': '^$',
        'files': '',
        'id': 'bash_hook',
        'language': 'script',
        'language_version': 'default',
        'log_file': '',
        'minimum_pre_commit_version': '0',
        'name': 'Bash hook',
        'pass_filenames': True,
        'stages': [],
        'types': ['file'],
        'exclude_types': [],
    }
