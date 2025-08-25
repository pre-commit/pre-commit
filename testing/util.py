from __future__ import annotations

import contextlib
import os.path
import subprocess
import sys

import pytest

from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple


TESTING_DIR = os.path.abspath(os.path.dirname(__file__))


def get_resource_path(path):
    return os.path.join(TESTING_DIR, 'resources', path)


def cmd_output_mocked_pre_commit_home(
        *args, tempdir_factory, pre_commit_home=None, env=None, **kwargs,
):
    if pre_commit_home is None:
        pre_commit_home = tempdir_factory.get()
    env = env if env is not None else os.environ
    kwargs.setdefault('stderr', subprocess.STDOUT)
    # Don't want to write to the home directory
    env = dict(env, PRE_COMMIT_HOME=pre_commit_home)
    ret, out, _ = cmd_output(*args, env=env, **kwargs)
    return ret, out.replace('\r\n', '\n'), None


xfailif_windows = pytest.mark.xfail(sys.platform == 'win32', reason='windows')


def run_opts(
        all_files=False,
        files=(),
        color=False,
        verbose=False,
        hook=None,
        fail_fast=False,
        remote_branch='',
        local_branch='',
        from_ref='',
        to_ref='',
        pre_rebase_upstream='',
        pre_rebase_branch='',
        remote_name='',
        remote_url='',
        hook_stage='pre-commit',
        show_diff_on_failure=False,
        commit_msg_filename='',
        prepare_commit_message_source='',
        commit_object_name='',
        checkout_type='',
        is_squash_merge='',
        rewrite_command='',
):
    # These are mutually exclusive
    assert not (all_files and files)
    return auto_namedtuple(
        all_files=all_files,
        files=files,
        color=color,
        verbose=verbose,
        hook=hook,
        fail_fast=fail_fast,
        remote_branch=remote_branch,
        local_branch=local_branch,
        from_ref=from_ref,
        to_ref=to_ref,
        pre_rebase_upstream=pre_rebase_upstream,
        pre_rebase_branch=pre_rebase_branch,
        remote_name=remote_name,
        remote_url=remote_url,
        hook_stage=hook_stage,
        show_diff_on_failure=show_diff_on_failure,
        commit_msg_filename=commit_msg_filename,
        prepare_commit_message_source=prepare_commit_message_source,
        commit_object_name=commit_object_name,
        checkout_type=checkout_type,
        is_squash_merge=is_squash_merge,
        rewrite_command=rewrite_command,
    )


@contextlib.contextmanager
def cwd(path):
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)


def git_commit(*args, fn=cmd_output, msg='commit!', all_files=True, **kwargs):
    kwargs.setdefault('stderr', subprocess.STDOUT)

    cmd = ('git', 'commit', '--allow-empty', '--no-gpg-sign', *args)
    if all_files:  # allow skipping `-a` with `all_files=False`
        cmd += ('-a',)
    if msg is not None:  # allow skipping `-m` with `msg=None`
        cmd += ('-m', msg)
    ret, out, _ = fn(*cmd, **kwargs)
    return ret, out.replace('\r\n', '\n')
