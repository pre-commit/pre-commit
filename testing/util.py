import contextlib
import os.path
import subprocess

import pytest

from pre_commit import parse_shebang
from pre_commit.languages.docker import docker_is_running
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


skipif_cant_run_docker = pytest.mark.skipif(
    os.name == 'nt' or not docker_is_running(),
    reason="Docker isn't running or can't be accessed",
)
skipif_cant_run_swift = pytest.mark.skipif(
    parse_shebang.find_executable('swift') is None,
    reason="swift isn't installed or can't be found",
)
xfailif_windows_no_ruby = pytest.mark.xfail(
    os.name == 'nt',
    reason='Ruby support not yet implemented on windows.',
)
xfailif_windows = pytest.mark.xfail(os.name == 'nt', reason='windows')


def supports_venv():  # pragma: no cover (platform specific)
    try:
        __import__('ensurepip')
        __import__('venv')
        return True
    except ImportError:
        return False


xfailif_no_venv = pytest.mark.xfail(
    not supports_venv(), reason='Does not support venv module',
)


def run_opts(
        all_files=False,
        files=(),
        color=False,
        verbose=False,
        hook=None,
        from_ref='',
        to_ref='',
        remote_name='',
        remote_url='',
        hook_stage='commit',
        show_diff_on_failure=False,
        commit_msg_filename='',
        checkout_type='',
):
    # These are mutually exclusive
    assert not (all_files and files)
    return auto_namedtuple(
        all_files=all_files,
        files=files,
        color=color,
        verbose=verbose,
        hook=hook,
        from_ref=from_ref,
        to_ref=to_ref,
        remote_name=remote_name,
        remote_url=remote_url,
        hook_stage=hook_stage,
        show_diff_on_failure=show_diff_on_failure,
        commit_msg_filename=commit_msg_filename,
        checkout_type=checkout_type,
    )


@contextlib.contextmanager
def cwd(path):
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)


def git_commit(*args, fn=cmd_output, msg='commit!', **kwargs):
    kwargs.setdefault('stderr', subprocess.STDOUT)

    cmd = ('git', 'commit', '--allow-empty', '--no-gpg-sign', '-a') + args
    if msg is not None:  # allow skipping `-m` with `msg=None`
        cmd += ('-m', msg)
    ret, out, _ = fn(*cmd, **kwargs)
    return ret, out.replace('\r\n', '\n')
