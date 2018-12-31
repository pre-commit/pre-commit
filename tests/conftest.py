from __future__ import absolute_import
from __future__ import unicode_literals

import functools
import io
import logging
import os.path

import mock
import pytest
import six

from pre_commit import output
from pre_commit.logging_handler import add_logging_handler
from pre_commit.store import Store
from pre_commit.util import cmd_output
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo
from testing.fixtures import write_config
from testing.util import cwd
from testing.util import git_commit


@pytest.fixture(autouse=True)
def no_warnings(recwarn):
    yield
    warnings = []
    for warning in recwarn:  # pragma: no cover
        message = str(warning.message)
        # ImportWarning: Not importing directory '...' missing __init__(.py)
        if not (
            isinstance(warning.message, ImportWarning)
            and message.startswith('Not importing directory ')
            and ' missing __init__' in message
        ):
            warnings.append('{}:{} {}'.format(
                warning.filename,
                warning.lineno,
                message,
            ))
    assert not warnings


@pytest.fixture
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


@pytest.fixture
def in_tmpdir(tempdir_factory):
    path = tempdir_factory.get()
    with cwd(path):
        yield path


@pytest.fixture
def in_git_dir(tmpdir):
    repo = tmpdir.join('repo').ensure_dir()
    with repo.as_cwd():
        cmd_output('git', 'init')
        yield repo


def _make_conflict():
    cmd_output('git', 'checkout', 'origin/master', '-b', 'foo')
    with io.open('conflict_file', 'w') as conflict_file:
        conflict_file.write('herp\nderp\n')
    cmd_output('git', 'add', 'conflict_file')
    with io.open('foo_only_file', 'w') as foo_only_file:
        foo_only_file.write('foo')
    cmd_output('git', 'add', 'foo_only_file')
    git_commit(msg=_make_conflict.__name__)
    cmd_output('git', 'checkout', 'origin/master', '-b', 'bar')
    with io.open('conflict_file', 'w') as conflict_file:
        conflict_file.write('harp\nddrp\n')
    cmd_output('git', 'add', 'conflict_file')
    with io.open('bar_only_file', 'w') as bar_only_file:
        bar_only_file.write('bar')
    cmd_output('git', 'add', 'bar_only_file')
    git_commit(msg=_make_conflict.__name__)
    cmd_output('git', 'merge', 'foo', retcode=None)


@pytest.fixture
def in_merge_conflict(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    open(os.path.join(path, 'dummy'), 'a').close()
    cmd_output('git', 'add', 'dummy', cwd=path)
    git_commit(msg=in_merge_conflict.__name__, cwd=path)

    conflict_path = tempdir_factory.get()
    cmd_output('git', 'clone', path, conflict_path)
    with cwd(conflict_path):
        _make_conflict()
        yield os.path.join(conflict_path)


@pytest.fixture
def in_conflicting_submodule(tempdir_factory):
    git_dir_1 = git_dir(tempdir_factory)
    git_dir_2 = git_dir(tempdir_factory)
    git_commit(msg=in_conflicting_submodule.__name__, cwd=git_dir_2)
    cmd_output('git', 'submodule', 'add', git_dir_2, 'sub', cwd=git_dir_1)
    with cwd(os.path.join(git_dir_1, 'sub')):
        _make_conflict()
        yield


@pytest.fixture
def commit_msg_repo(tempdir_factory):
    path = git_dir(tempdir_factory)
    config = {
        'repo': 'local',
        'hooks': [{
            'id': 'must-have-signoff',
            'name': 'Must have "Signed off by:"',
            'entry': 'grep -q "Signed off by:"',
            'language': 'system',
            'stages': ['commit-msg'],
        }],
    }
    write_config(path, config)
    with cwd(path):
        cmd_output('git', 'add', '.')
        git_commit(msg=commit_msg_repo.__name__)
        yield path


@pytest.fixture(autouse=True, scope='session')
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


@pytest.fixture
def mock_store_dir(tempdir_factory):
    tmpdir = tempdir_factory.get()
    with mock.patch.object(
        Store,
        'get_default_directory',
        return_value=tmpdir,
    ):
        yield tmpdir


@pytest.fixture
def store(tempdir_factory):
    yield Store(os.path.join(tempdir_factory.get(), '.pre-commit'))


@pytest.fixture
def log_info_mock():
    with mock.patch.object(logging.getLogger('pre_commit'), 'info') as mck:
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
        self._stream.data.seek(0)
        self._stream.data.truncate()
        return data

    def get(self):
        """Get the output assuming it was written as UTF-8 bytes"""
        return self.get_bytes().decode('UTF-8')


@pytest.fixture
def cap_out():
    stream = FakeStream()
    write = functools.partial(output.write, stream=stream)
    write_line = functools.partial(output.write_line, stream=stream)
    with mock.patch.object(output, 'write', write):
        with mock.patch.object(output, 'write_line', write_line):
            yield Fixture(stream)


@pytest.fixture
def fake_log_handler():
    handler = mock.Mock(level=logging.INFO)
    logger = logging.getLogger('pre_commit')
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)
