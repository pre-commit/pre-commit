from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
import re

from pre_commit.commands.try_repo import try_repo
from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import git_dir
from testing.fixtures import make_repo
from testing.util import cwd
from testing.util import run_opts


def try_repo_opts(repo, ref=None, **kwargs):
    return auto_namedtuple(repo=repo, ref=ref, **run_opts(**kwargs)._asdict())


def _get_out(cap_out):
    out = cap_out.get().replace('\r\n', '\n')
    out = re.sub('\[INFO\].+\n', '', out)
    start, using_config, config, rest = out.split('=' * 79 + '\n')
    assert start == ''
    assert using_config == 'Using config:\n'
    return config, rest


def _run_try_repo(tempdir_factory, **kwargs):
    repo = make_repo(tempdir_factory, 'modified_file_returns_zero_repo')
    with cwd(git_dir(tempdir_factory)):
        open('test-file', 'a').close()
        cmd_output('git', 'add', '.')
        assert not try_repo(try_repo_opts(repo, **kwargs))


def test_try_repo_repo_only(cap_out, tempdir_factory):
    _run_try_repo(tempdir_factory, verbose=True)
    config, rest = _get_out(cap_out)
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
    assert rest == (
        '[bash_hook] Bash hook................................(no files to check)Skipped\n'  # noqa
        '[bash_hook2] Bash hook...................................................Passed\n'  # noqa
        'hookid: bash_hook2\n'
        '\n'
        'test-file\n'
        '\n'
        '[bash_hook3] Bash hook...............................(no files to check)Skipped\n'  # noqa
    )


def test_try_repo_with_specific_hook(cap_out, tempdir_factory):
    _run_try_repo(tempdir_factory, hook='bash_hook', verbose=True)
    config, rest = _get_out(cap_out)
    assert re.match(
        '^repos:\n'
        '-   repo: .+\n'
        '    rev: .+\n'
        '    hooks:\n'
        '    -   id: bash_hook\n$',
        config,
    )
    assert rest == '[bash_hook] Bash hook................................(no files to check)Skipped\n'  # noqa


def test_try_repo_relative_path(cap_out, tempdir_factory):
    repo = make_repo(tempdir_factory, 'modified_file_returns_zero_repo')
    with cwd(git_dir(tempdir_factory)):
        open('test-file', 'a').close()
        cmd_output('git', 'add', '.')
        relative_repo = os.path.relpath(repo, '.')
        # previously crashed on cloning a relative path
        assert not try_repo(try_repo_opts(relative_repo, hook='bash_hook'))
