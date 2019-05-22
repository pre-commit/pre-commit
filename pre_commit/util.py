from __future__ import unicode_literals

import contextlib
import errno
import os.path
import shutil
import stat
import subprocess
import sys
import tempfile

import six

from pre_commit import five
from pre_commit import parse_shebang

if sys.version_info >= (3, 7):  # pragma: no cover (PY37+)
    from importlib.resources import open_binary
    from importlib.resources import read_text
else:  # pragma: no cover (<PY37)
    from importlib_resources import open_binary
    from importlib_resources import read_text


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.exists(path):
            raise


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


def resource_bytesio(filename):
    return open_binary('pre_commit.resources', filename)


def resource_text(filename):
    return read_text('pre_commit.resources', filename)


def make_executable(filename):
    original_mode = os.stat(filename).st_mode
    os.chmod(
        filename, original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
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

    def to_bytes(self):
        output = []
        for maybe_text in self.output:
            if maybe_text:
                output.append(
                    b'\n    ' +
                    five.to_bytes(maybe_text).replace(b'\n', b'\n    '),
                )
            else:
                output.append(b'(none)')

        return b''.join((
            five.to_bytes(
                'Command: {!r}\n'
                'Return code: {}\n'
                'Expected return code: {}\n'.format(
                    self.cmd, self.returncode, self.expected_returncode,
                ),
            ),
            b'Output: ', output[0], b'\n',
            b'Errors: ', output[1], b'\n',
        ))

    def to_text(self):
        return self.to_bytes().decode('UTF-8')

    if six.PY2:  # pragma: no cover (py2)
        __str__ = to_bytes
        __unicode__ = to_text
    else:  # pragma: no cover (py3)
        __bytes__ = to_bytes
        __str__ = to_text


def cmd_output(*cmd, **kwargs):
    retcode = kwargs.pop('retcode', 0)
    encoding = kwargs.pop('encoding', 'UTF-8')

    popen_kwargs = {
        'stdin': subprocess.PIPE,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
    }

    # py2/py3 on windows are more strict about the types here
    cmd = tuple(five.n(arg) for arg in cmd)
    kwargs['env'] = {
        five.n(key): five.n(value)
        for key, value in kwargs.pop('env', {}).items()
    } or None

    try:
        cmd = parse_shebang.normalize_cmd(cmd)
    except parse_shebang.ExecutableNotFoundError as e:
        returncode, stdout, stderr = e.to_output()
    else:
        popen_kwargs.update(kwargs)
        proc = subprocess.Popen(cmd, **popen_kwargs)
        stdout, stderr = proc.communicate()
        returncode = proc.returncode
    if encoding is not None and stdout is not None:
        stdout = stdout.decode(encoding)
    if encoding is not None and stderr is not None:
        stderr = stderr.decode(encoding)

    if retcode is not None and retcode != returncode:
        raise CalledProcessError(
            returncode, cmd, retcode, output=(stdout, stderr),
        )

    return returncode, stdout, stderr


def rmtree(path):
    """On windows, rmtree fails for readonly dirs."""
    def handle_remove_readonly(func, path, exc):
        excvalue = exc[1]
        if (
                func in (os.rmdir, os.remove, os.unlink) and
                excvalue.errno == errno.EACCES
        ):
            for p in (path, os.path.dirname(path)):
                os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)
            func(path)
        else:
            raise
    shutil.rmtree(path, ignore_errors=False, onerror=handle_remove_readonly)


def parse_version(s):
    """poor man's version comparison"""
    return tuple(int(p) for p in s.split('.'))
