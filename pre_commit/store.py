from __future__ import unicode_literals

import contextlib
import io
import logging
import os.path
import sqlite3
import tempfile

import pre_commit.constants as C
from pre_commit import file_lock
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import copy_tree_to_path
from pre_commit.util import no_git_env
from pre_commit.util import resource_filename


logger = logging.getLogger('pre_commit')


def _get_default_directory():
    """Returns the default directory for the Store.  This is intentionally
    underscored to indicate that `Store.get_default_directory` is the intended
    way to get this information.  This is also done so
    `Store.get_default_directory` can be mocked in tests and
    `_get_default_directory` can be tested.
    """
    return os.environ.get('PRE_COMMIT_HOME') or os.path.join(
        os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache'),
        'pre-commit',
    )


class Store(object):
    get_default_directory = staticmethod(_get_default_directory)
    __created = False

    def __init__(self, directory=None):
        self.directory = directory or Store.get_default_directory()

    @contextlib.contextmanager
    def exclusive_lock(self):
        def blocked_cb():  # pragma: no cover (tests are single-process)
            logger.info('Locking pre-commit directory')

        with file_lock.lock(os.path.join(self.directory, '.lock'), blocked_cb):
            yield

    def _write_readme(self):
        with io.open(os.path.join(self.directory, 'README'), 'w') as readme:
            readme.write(
                'This directory is maintained by the pre-commit project.\n'
                'Learn more: https://github.com/pre-commit/pre-commit\n',
            )

    def _write_sqlite_db(self):
        # To avoid a race where someone ^Cs between db creation and execution
        # of the CREATE TABLE statement
        fd, tmpfile = tempfile.mkstemp(dir=self.directory)
        # We'll be managing this file ourselves
        os.close(fd)
        # sqlite doesn't close its fd with its contextmanager >.<
        # contextlib.closing fixes this.
        # See: https://stackoverflow.com/a/28032829/812183
        with contextlib.closing(sqlite3.connect(tmpfile)) as db:
            db.executescript(
                'CREATE TABLE repos ('
                '    repo TEXT NOT NULL,'
                '    ref TEXT NOT NULL,'
                '    path TEXT NOT NULL,'
                '    PRIMARY KEY (repo, ref)'
                ');',
            )

        # Atomic file move
        os.rename(tmpfile, self.db_path)

    def _create(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            self._write_readme()

        if os.path.exists(self.db_path):
            return
        with self.exclusive_lock():
            # Another process may have already completed this work
            if os.path.exists(self.db_path):  # pragma: no cover (race)
                return
            self._write_sqlite_db()

    def require_created(self):
        """Require the pre-commit file store to be created."""
        if not self.__created:
            self._create()
            self.__created = True

    def _new_repo(self, repo, ref, deps, make_strategy):
        self.require_created()
        if deps:
            repo = '{}:{}'.format(repo, ','.join(sorted(deps)))

        def _get_result():
            # Check if we already exist
            with sqlite3.connect(self.db_path) as db:
                result = db.execute(
                    'SELECT path FROM repos WHERE repo = ? AND ref = ?',
                    (repo, ref),
                ).fetchone()
                if result:
                    return result[0]

        result = _get_result()
        if result:
            return result
        with self.exclusive_lock():
            # Another process may have already completed this work
            result = _get_result()
            if result:  # pragma: no cover (race)
                return result

            logger.info('Initializing environment for {}.'.format(repo))

            directory = tempfile.mkdtemp(prefix='repo', dir=self.directory)
            with clean_path_on_failure(directory):
                make_strategy(directory)

            # Update our db with the created repo
            with sqlite3.connect(self.db_path) as db:
                db.execute(
                    'INSERT INTO repos (repo, ref, path) VALUES (?, ?, ?)',
                    [repo, ref, directory],
                )
        return directory

    def clone(self, repo, ref, deps=()):
        """Clone the given url and checkout the specific ref."""
        def clone_strategy(directory):
            env = no_git_env()

            cmd = ('git', 'clone', '--no-checkout', repo, directory)
            cmd_output(*cmd, env=env)

            def _git_cmd(*args):
                return cmd_output('git', *args, cwd=directory, env=env)

            _git_cmd('reset', ref, '--hard')
            _git_cmd('submodule', 'update', '--init', '--recursive')

        return self._new_repo(repo, ref, deps, clone_strategy)

    def make_local(self, deps):
        def make_local_strategy(directory):
            copy_tree_to_path(resource_filename('empty_template'), directory)

            env = no_git_env()
            name, email = 'pre-commit', 'asottile+pre-commit@umich.edu'
            env['GIT_AUTHOR_NAME'] = env['GIT_COMMITTER_NAME'] = name
            env['GIT_AUTHOR_EMAIL'] = env['GIT_COMMITTER_EMAIL'] = email

            # initialize the git repository so it looks more like cloned repos
            def _git_cmd(*args):
                cmd_output('git', *args, cwd=directory, env=env)

            _git_cmd('init', '.')
            _git_cmd('config', 'remote.origin.url', '<<unknown>>')
            _git_cmd('add', '.')
            _git_cmd('commit', '--no-edit', '--no-gpg-sign', '-n', '-minit')

        return self._new_repo(
            'local', C.LOCAL_REPO_VERSION, deps, make_local_strategy,
        )

    @property
    def db_path(self):
        return os.path.join(self.directory, 'db.db')
