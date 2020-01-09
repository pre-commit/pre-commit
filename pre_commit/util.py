import contextlib
import errno
import os.path
import shutil
import stat
import subprocess
import sys
import tempfile

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
    def __init__(self, returncode, cmd, expected_returncode, stdout, stderr):
        super().__init__(
            returncode, cmd, expected_returncode, stdout, stderr,
        )
        self.returncode = returncode
        self.cmd = cmd
        self.expected_returncode = expected_returncode
        self.stdout = stdout
        self.stderr = stderr

    def __bytes__(self):
        def _indent_or_none(part):
            if part:
                return b'\n    ' + part.replace(b'\n', b'\n    ')
            else:
                return b' (none)'

        return b''.join((
            'command: {!r}\n'
            'return code: {}\n'
            'expected return code: {}\n'.format(
                self.cmd, self.returncode, self.expected_returncode,
            ).encode('UTF-8'),
            b'stdout:', _indent_or_none(self.stdout), b'\n',
            b'stderr:', _indent_or_none(self.stderr),
        ))

    def __str__(self):
        return self.__bytes__().decode('UTF-8')


def _cmd_kwargs(*cmd, **kwargs):
    # py2/py3 on windows are more strict about the types here
    cmd = tuple(five.n(arg) for arg in cmd)
    kwargs['env'] = {
        five.n(key): five.n(value)
        for key, value in kwargs.pop('env', {}).items()
    } or None
    for arg in ('stdin', 'stdout', 'stderr'):
        kwargs.setdefault(arg, subprocess.PIPE)
    return cmd, kwargs


def cmd_output_b(*cmd, **kwargs):
    retcode = kwargs.pop('retcode', 0)
    cmd, kwargs = _cmd_kwargs(*cmd, **kwargs)

    try:
        cmd = parse_shebang.normalize_cmd(cmd)
    except parse_shebang.ExecutableNotFoundError as e:
        returncode, stdout_b, stderr_b = e.to_output()
    else:
        proc = subprocess.Popen(cmd, **kwargs)
        stdout_b, stderr_b = proc.communicate()
        returncode = proc.returncode

    if retcode is not None and retcode != returncode:
        raise CalledProcessError(returncode, cmd, retcode, stdout_b, stderr_b)

    return returncode, stdout_b, stderr_b


def cmd_output(*cmd, **kwargs):
    returncode, stdout_b, stderr_b = cmd_output_b(*cmd, **kwargs)
    stdout = stdout_b.decode('UTF-8') if stdout_b is not None else None
    stderr = stderr_b.decode('UTF-8') if stderr_b is not None else None
    return returncode, stdout, stderr


if os.name != 'nt':  # pragma: windows no cover
    from os import openpty
    import termios

    class Pty:
        def __init__(self):
            self.r = self.w = None

        def __enter__(self):
            self.r, self.w = openpty()

            # tty flags normally change \n to \r\n
            attrs = termios.tcgetattr(self.r)
            attrs[1] &= ~(termios.ONLCR | termios.OPOST)
            termios.tcsetattr(self.r, termios.TCSANOW, attrs)

            return self

        def close_w(self):
            if self.w is not None:
                os.close(self.w)
                self.w = None

        def close_r(self):
            assert self.r is not None
            os.close(self.r)
            self.r = None

        def __exit__(self, exc_type, exc_value, traceback):
            self.close_w()
            self.close_r()

    def cmd_output_p(*cmd, **kwargs):
        assert kwargs.pop('retcode') is None
        assert kwargs['stderr'] == subprocess.STDOUT, kwargs['stderr']
        cmd, kwargs = _cmd_kwargs(*cmd, **kwargs)

        try:
            cmd = parse_shebang.normalize_cmd(cmd)
        except parse_shebang.ExecutableNotFoundError as e:
            return e.to_output()

        with open(os.devnull) as devnull, Pty() as pty:
            kwargs.update({'stdin': devnull, 'stdout': pty.w, 'stderr': pty.w})
            proc = subprocess.Popen(cmd, **kwargs)
            pty.close_w()

            buf = b''
            while True:
                try:
                    bts = os.read(pty.r, 4096)
                except OSError as e:
                    if e.errno == errno.EIO:
                        bts = b''
                    else:
                        raise
                else:
                    buf += bts
                if not bts:
                    break

        return proc.wait(), buf, None
else:  # pragma: no cover
    cmd_output_p = cmd_output_b


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
