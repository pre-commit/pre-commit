import os.path
import re
import time

import mock

from pre_commit import git
from pre_commit.commands.try_repo import try_repo
from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import git_dir
from testing.fixtures import make_repo
from testing.fixtures import modify_manifest
from testing.util import cwd
from testing.util import git_commit
from testing.util import run_opts


def try_repo_opts(repo, ref=None, **kwargs):
    return auto_namedtuple(repo=repo, ref=ref, **run_opts(**kwargs)._asdict())


def _get_out(cap_out):
    out = re.sub(r'\[INFO\].+\n', '', cap_out.get())
    start, using_config, config, rest = out.split('=' * 79 + '\n')
    assert using_config == 'Using config:\n'
    return start, config, rest


def _add_test_file():
    open('test-file', 'a').close()
    cmd_output('git', 'add', '.')


def _run_try_repo(tempdir_factory, **kwargs):
    repo = make_repo(tempdir_factory, 'modified_file_returns_zero_repo')
    with cwd(git_dir(tempdir_factory)):
        _add_test_file()
        assert not try_repo(try_repo_opts(repo, **kwargs))


def test_try_repo_repo_only(cap_out, tempdir_factory):
    with mock.patch.object(time, 'time', return_value=0.0):
        _run_try_repo(tempdir_factory, verbose=True)
    start, config, rest = _get_out(cap_out)
    assert start == ''
    assert re.match(
        '^repos:\n'
        '-   repo: .+\n'
        '    rev: .+\n'
        '    hooks:\n'
        '    -   id: bash_hook\n'
        '    -   id: bash_hook2\n'
        '    -   id: bash_hook3\n$',
        config,
    )
    assert rest == '''\
Bash hook............................................(no files to check)Skipped
- hook id: bash_hook
Bash hook................................................................Passed
- hook id: bash_hook2
- duration: 0s

test-file

Bash hook............................................(no files to check)Skipped
- hook id: bash_hook3
'''


def test_try_repo_with_specific_hook(cap_out, tempdir_factory):
    _run_try_repo(tempdir_factory, hook='bash_hook', verbose=True)
    start, config, rest = _get_out(cap_out)
    assert start == ''
    assert re.match(
        '^repos:\n'
        '-   repo: .+\n'
        '    rev: .+\n'
        '    hooks:\n'
        '    -   id: bash_hook\n$',
        config,
    )
    assert rest == '''\
Bash hook............................................(no files to check)Skipped
- hook id: bash_hook
'''


def test_try_repo_relative_path(cap_out, tempdir_factory):
    repo = make_repo(tempdir_factory, 'modified_file_returns_zero_repo')
    with cwd(git_dir(tempdir_factory)):
        _add_test_file()
        relative_repo = os.path.relpath(repo, '.')
        # previously crashed on cloning a relative path
        assert not try_repo(try_repo_opts(relative_repo, hook='bash_hook'))


def test_try_repo_bare_repo(cap_out, tempdir_factory):
    repo = make_repo(tempdir_factory, 'modified_file_returns_zero_repo')
    with cwd(git_dir(tempdir_factory)):
        _add_test_file()
        bare_repo = os.path.join(repo, '.git')
        # previously crashed attempting modification changes
        assert not try_repo(try_repo_opts(bare_repo, hook='bash_hook'))


def test_try_repo_specific_revision(cap_out, tempdir_factory):
    repo = make_repo(tempdir_factory, 'script_hooks_repo')
    ref = git.head_rev(repo)
    git_commit(cwd=repo)
    with cwd(git_dir(tempdir_factory)):
        _add_test_file()
        assert not try_repo(try_repo_opts(repo, ref=ref))

    _, config, _ = _get_out(cap_out)
    assert ref in config


def test_try_repo_uncommitted_changes(cap_out, tempdir_factory):
    repo = make_repo(tempdir_factory, 'script_hooks_repo')
    # make an uncommitted change
    with modify_manifest(repo, commit=False) as manifest:
        manifest[0]['name'] = 'modified name!'

    with cwd(git_dir(tempdir_factory)):
        open('test-fie', 'a').close()
        cmd_output('git', 'add', '.')
        assert not try_repo(try_repo_opts(repo))

    start, config, rest = _get_out(cap_out)
    assert start == '[WARNING] Creating temporary repo with uncommitted changes...\n'  # noqa: E501
    assert re.match(
        '^repos:\n'
        '-   repo: .+shadow-repo\n'
        '    rev: .+\n'
        '    hooks:\n'
        '    -   id: bash_hook\n$',
        config,
    )
    assert rest == 'modified name!...........................................................Passed\n'  # noqa: E501


def test_try_repo_staged_changes(tempdir_factory):
    repo = make_repo(tempdir_factory, 'modified_file_returns_zero_repo')

    with cwd(repo):
        open('staged-file', 'a').close()
        open('second-staged-file', 'a').close()
        cmd_output('git', 'add', '.')

    with cwd(git_dir(tempdir_factory)):
        assert not try_repo(try_repo_opts(repo, hook='bash_hook'))
