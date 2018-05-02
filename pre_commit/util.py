from __future__ import unicode_literals

import contextlib
import errno
import functools
import os.path
import shutil
import stat
import subprocess
import tempfile

import pkg_resources
import six

from pre_commit import five
from pre_commit import parse_shebang


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        if not os.path.exists(path):
            raise


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


def no_git_env():
    # Too many bugs dealing with environment variables and GIT:
    # https://github.com/pre-commit/pre-commit/issues/300
    # In git 2.6.3 (maybe others), git exports GIT_WORK_TREE while running
    # pre-commit hooks
    # In git 1.9.1 (maybe others), git exports GIT_DIR and GIT_INDEX_FILE
    # while running pre-commit hooks in submodules.
    # GIT_DIR: Causes git clone to clone wrong thing
    # GIT_INDEX_FILE: Causes 'error invalid object ...' during commit
    return {
        k: v for k, v in os.environ.items()
        if not k.startswith('GIT_') or k in {'GIT_SSH'}
    }


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


def resource_filename(*segments):
    return pkg_resources.resource_filename(
        'pre_commit', os.path.join('resources', *segments),
    )


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
    def handle_remove_readonly(func, path, exc):  # pragma: no cover (windows)
        excvalue = exc[1]
        if (
                func in (os.rmdir, os.remove, os.unlink) and
                excvalue.errno == errno.EACCES
        ):
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            func(path)
        else:
            raise
    shutil.rmtree(path, ignore_errors=False, onerror=handle_remove_readonly)


def copy_tree_to_path(src_dir, dest_dir):
    """Copies all of the things inside src_dir to an already existing dest_dir.

    This looks eerily similar to shutil.copytree, but copytree has no option
    for not creating dest_dir.
    """
    names = os.listdir(src_dir)

    for name in names:
        srcname = os.path.join(src_dir, name)
        destname = os.path.join(dest_dir, name)

        if os.path.isdir(srcname):
            shutil.copytree(srcname, destname)
        else:
            shutil.copy(srcname, destname)
