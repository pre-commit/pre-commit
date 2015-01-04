from __future__ import unicode_literals

import contextlib
import functools
import hashlib
import os
import os.path
import shutil
import subprocess
import tarfile
import tempfile

import pkg_resources


@contextlib.contextmanager
def cwd(path):
    original_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(original_cwd)


def memoize_by_cwd(func):
    """Memoize a function call based on os.getcwd()."""
    @functools.wraps(func)
    def wrapper(*args):
        cwd = os.getcwd()
        key = (cwd,) + args
        try:
            return wrapper._cache[key]
        except KeyError:
            ret = wrapper._cache[key] = func(*args)
            return ret

    wrapper._cache = {}

    return wrapper


@contextlib.contextmanager
def clean_path_on_failure(path):
    """Cleans up the directory on an exceptional failure."""
    try:
        yield
    except BaseException:
        if os.path.exists(path):
            shutil.rmtree(path)
        raise


@contextlib.contextmanager
def noop_context():
    yield


def shell_escape(arg):
    return "'" + arg.replace("'", "'\"'\"'".strip()) + "'"


def hex_md5(s):
    """Hexdigest an md5 of the string.

    :param text s:
    """
    return hashlib.md5(s.encode('utf-8')).hexdigest()


@contextlib.contextmanager
def tarfile_open(*args, **kwargs):
    """Compatibility layer because python2.6"""
    tf = tarfile.open(*args, **kwargs)
    try:
        yield tf
    finally:
        tf.close()


@contextlib.contextmanager
def tmpdir():
    """Contextmanager to create a temporary directory.  It will be cleaned up
    afterwards.
    """
    tempdir = tempfile.mkdtemp()
    try:
        yield tempdir
    finally:
        shutil.rmtree(tempdir)


def resource_filename(filename):
    return pkg_resources.resource_filename(
        'pre_commit',
        os.path.join('resources', filename),
    )


class CalledProcessError(RuntimeError):
    def __init__(self, returncode, cmd, expected_returncode, output=None):
        super(CalledProcessError, self).__init__(
            returncode, cmd, expected_returncode, output,
        )
        self.returncode = returncode
        self.cmd = cmd
        self.expected_returncode = expected_returncode
        self.output = output

    def __str__(self):
        return (
            'Command: {0!r}\n'
            'Return code: {1}\n'
            'Expected return code: {2}\n'
            'Output: {3!r}\n'.format(
                self.cmd,
                self.returncode,
                self.expected_returncode,
                self.output,
            )
        )


def cmd_output(*cmd, **kwargs):
    retcode = kwargs.pop('retcode', 0)
    stdin = kwargs.pop('stdin', None)
    encoding = kwargs.pop('encoding', 'UTF-8')
    __popen = kwargs.pop('__popen', subprocess.Popen)

    popen_kwargs = {
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
    }

    if stdin is not None:
        stdin = stdin.encode('UTF-8')

    popen_kwargs.update(kwargs)
    proc = __popen(cmd, **popen_kwargs)
    stdout, stderr = proc.communicate(stdin)
    if encoding is not None and stdout is not None:
        stdout = stdout.decode(encoding)
    if encoding is not None and stderr is not None:
        stderr = stderr.decode(encoding)
    returncode = proc.returncode

    if retcode is not None and retcode != returncode:
        raise CalledProcessError(
            returncode, cmd, retcode, output=(stdout, stderr),
        )

    return proc.returncode, stdout, stderr
