from __future__ import unicode_literals

import contextlib
import os.path
import sys

import pytest

from pre_commit import parse_shebang
from pre_commit.languages.docker import docker_is_running
from pre_commit.languages.pcre import GREP
from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple


TESTING_DIR = os.path.abspath(os.path.dirname(__file__))


def get_resource_path(path):
    return os.path.join(TESTING_DIR, 'resources', path)


def cmd_output_mocked_pre_commit_home(*args, **kwargs):
    # keyword-only argument
    tempdir_factory = kwargs.pop('tempdir_factory')
    pre_commit_home = kwargs.pop('pre_commit_home', tempdir_factory.get())
    # Don't want to write to the home directory
    env = dict(kwargs.pop('env', os.environ), PRE_COMMIT_HOME=pre_commit_home)
    return cmd_output(*args, env=env, **kwargs)


skipif_cant_run_docker = pytest.mark.skipif(
    docker_is_running() is False,
    reason='Docker isn\'t running or can\'t  be accessed',
)

skipif_cant_run_swift = pytest.mark.skipif(
    parse_shebang.find_executable('swift') is None,
    reason='swift isn\'t installed or can\'t be found',
)

xfailif_windows_no_ruby = pytest.mark.xfail(
    os.name == 'nt',
    reason='Ruby support not yet implemented on windows.',
)


def broken_deep_listdir():  # pragma: no cover (platform specific)
    if sys.platform != 'win32':
        return False
    return True  # see #798


xfailif_broken_deep_listdir = pytest.mark.xfail(
    broken_deep_listdir(),
    reason='Node on windows requires deep listdir',
)


def platform_supports_pcre():
    output = cmd_output(GREP, '-P', "name='pre", 'setup.py', retcode=None)
    return output[0] == 0 and "name='pre_commit'," in output[1]


xfailif_no_pcre_support = pytest.mark.xfail(
    not platform_supports_pcre(),
    reason='grep -P is not supported on this platform',
)

xfailif_no_symlink = pytest.mark.xfail(
    not hasattr(os, 'symlink'),
    reason='Symlink is not supported on this platform',
)


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
        origin='',
        source='',
        hook_stage='commit',
        show_diff_on_failure=False,
        commit_msg_filename='',
):
    # These are mutually exclusive
    assert not (all_files and files)
    return auto_namedtuple(
        all_files=all_files,
        files=files,
        color=color,
        verbose=verbose,
        hook=hook,
        origin=origin,
        source=source,
        hook_stage=hook_stage,
        show_diff_on_failure=show_diff_on_failure,
        commit_msg_filename=commit_msg_filename,
    )


@contextlib.contextmanager
def cwd(path):
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)
