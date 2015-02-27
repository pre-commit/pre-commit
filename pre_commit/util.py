from __future__ import unicode_literals

import contextlib
import errno
import functools
import os
import os.path
import shutil
import stat
import subprocess
import tarfile
import tempfile

import pkg_resources

from pre_commit import five


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
            rmtree(path)
        raise


@contextlib.contextmanager
def noop_context():
    yield


def shell_escape(arg):
    return "'" + arg.replace("'", "'\"'\"'".strip()) + "'"


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
        rmtree(tempdir)


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
        output = []
        for text in self.output:
            if text:
                output.append('\n    ' + text.replace('\n', '\n    '))
            else:
                output.append('(none)')

        return (
            'Command: {0!r}\n'
            'Return code: {1}\n'
            'Expected return code: {2}\n'
            'Output: {3}\n'
            'Errors: {4}\n'.format(
                self.cmd,
                self.returncode,
                self.expected_returncode,
                *output
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

    # py2/py3 on windows are more strict about the types here
    cmd = [five.n(arg) for arg in cmd]
    kwargs['env'] = dict(
        (five.n(key), five.n(value))
        for key, value in kwargs.pop('env', {}).items()
    ) or None

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


def rmtree(path):
    """On windows, rmtree fails for readonly dirs."""
    def handle_remove_readonly(func, path, exc):  # pragma: no cover (windows)
        excvalue = exc[1]
        if func in (os.rmdir, os.remove) and excvalue.errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            func(path)
        else:
            raise
    shutil.rmtree(path, ignore_errors=False, onerror=handle_remove_readonly)
