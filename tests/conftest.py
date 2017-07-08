from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import io
import logging
import os.path

import mock
import pytest
import six

import pre_commit.constants as C
from pre_commit import output
from pre_commit.logging_handler import add_logging_handler
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.runner import Runner
from pre_commit.store import Store
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo


@pytest.yield_fixture
def tempdir_factory(tmpdir):
    class TmpdirFactory(object):
        def __init__(self):
            self.tmpdir_count = 0

        def get(self):
            path = tmpdir.join(six.text_type(self.tmpdir_count)).strpath
            self.tmpdir_count += 1
            os.mkdir(path)
            return path

    yield TmpdirFactory()


@pytest.yield_fixture
def in_tmpdir(tempdir_factory):
    path = tempdir_factory.get()
    with cwd(path):
        yield path


def _make_conflict():
    cmd_output('git', 'checkout', 'origin/master', '-b', 'foo')
    with io.open('conflict_file', 'w') as conflict_file:
        conflict_file.write('herp\nderp\n')
    cmd_output('git', 'add', 'conflict_file')
    with io.open('foo_only_file', 'w') as foo_only_file:
        foo_only_file.write('foo')
    cmd_output('git', 'add', 'foo_only_file')
    cmd_output('git', 'commit', '-m', 'conflict_file')
    cmd_output('git', 'checkout', 'origin/master', '-b', 'bar')
    with io.open('conflict_file', 'w') as conflict_file:
        conflict_file.write('harp\nddrp\n')
    cmd_output('git', 'add', 'conflict_file')
    with io.open('bar_only_file', 'w') as bar_only_file:
        bar_only_file.write('bar')
    cmd_output('git', 'add', 'bar_only_file')
    cmd_output('git', 'commit', '-m', 'conflict_file')
    cmd_output('git', 'merge', 'foo', retcode=None)


@pytest.yield_fixture
def in_merge_conflict(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        open('dummy', 'a').close()
        cmd_output('git', 'add', 'dummy')
        cmd_output('git', 'commit', '-m', 'Add config.')

    conflict_path = tempdir_factory.get()
    cmd_output('git', 'clone', path, conflict_path)
    with cwd(conflict_path):
        _make_conflict()
        yield os.path.join(conflict_path)


@pytest.yield_fixture
def in_conflicting_submodule(tempdir_factory):
    git_dir_1 = git_dir(tempdir_factory)
    git_dir_2 = git_dir(tempdir_factory)
    with cwd(git_dir_2):
        cmd_output('git', 'commit', '--allow-empty', '-m', 'init!')
    with cwd(git_dir_1):
        cmd_output('git', 'submodule', 'add', git_dir_2, 'sub')
    with cwd(os.path.join(git_dir_1, 'sub')):
        _make_conflict()
        yield


@pytest.yield_fixture(autouse=True, scope='session')
def dont_write_to_home_directory():
    """pre_commit.store.Store will by default write to the home directory
    We'll mock out `Store.get_default_directory` to raise invariantly so we
    don't construct a `Store` object that writes to our home directory.
    """
    class YouForgotToExplicitlyChooseAStoreDirectory(AssertionError):
        pass

    with mock.patch.object(
        Store,
        'get_default_directory',
        side_effect=YouForgotToExplicitlyChooseAStoreDirectory,
    ):
        yield


@pytest.fixture(autouse=True, scope='session')
def configure_logging():
    add_logging_handler(use_color=False)


@pytest.yield_fixture
def mock_out_store_directory(tempdir_factory):
    tmpdir = tempdir_factory.get()
    with mock.patch.object(
        Store,
        'get_default_directory',
        return_value=tmpdir,
    ):
        yield tmpdir


@pytest.yield_fixture
def store(tempdir_factory):
    yield Store(os.path.join(tempdir_factory.get(), '.pre-commit'))


@pytest.yield_fixture
def cmd_runner(tempdir_factory):
    yield PrefixedCommandRunner(tempdir_factory.get())


@pytest.yield_fixture
def runner_with_mocked_store(mock_out_store_directory):
    yield Runner('/', C.CONFIG_FILE)


@pytest.yield_fixture
def log_info_mock():
    with mock.patch.object(logging.getLogger('pre_commit'), 'info') as mck:
        yield mck


@pytest.yield_fixture
def log_warning_mock():
    with mock.patch.object(logging.getLogger('pre_commit'), 'warning') as mck:
        yield mck


class FakeStream(object):
    def __init__(self):
        self.data = io.BytesIO()

    def write(self, s):
        self.data.write(s)

    def flush(self):
        pass


class Fixture(object):
    def __init__(self, stream):
        self._stream = stream

    def get_bytes(self):
        """Get the output as-if no encoding occurred"""
        data = self._stream.data.getvalue()
        self._stream = io.BytesIO()
        return data

    def get(self):
        """Get the output assuming it was written as UTF-8 bytes"""
        return self.get_bytes().decode('UTF-8')


@pytest.yield_fixture
def cap_out():
    stream = FakeStream()
    write = functools.partial(output.write, stream=stream)
    write_line = functools.partial(output.write_line, stream=stream)
    with mock.patch.object(output, 'write', write):
        with mock.patch.object(output, 'write_line', write_line):
            yield Fixture(stream)


@pytest.yield_fixture
def fake_log_handler():
    handler = mock.Mock(level=logging.INFO)
    logger = logging.getLogger('pre_commit')
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)
