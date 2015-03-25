from __future__ import unicode_literals

import contextlib
import io
import logging
import os
import os.path
import sqlite3
import tempfile

from cached_property import cached_property

from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import cwd


logger = logging.getLogger('pre_commit')


def _get_default_directory():
    """Returns the default directory for the Store.  This is intentionally
    underscored to indicate that `Store.get_default_directory` is the intended
    way to get this information.  This is also done so
    `Store.get_default_directory` can be mocked in tests and
    `_get_default_directory` can be tested.
    """
    return os.environ.get(
        'PRE_COMMIT_HOME',
        os.path.join(os.path.expanduser('~'), '.pre-commit'),
    )


class Store(object):
    get_default_directory = staticmethod(_get_default_directory)

    class RepoPathGetter(object):
        def __init__(self, repo, sha, store):
            self._repo = repo
            self._sha = sha
            self._store = store

        @cached_property
        def repo_path(self):
            return self._store.clone(self._repo, self._sha)

    def __init__(self, directory=None):
        if directory is None:
            directory = self.get_default_directory()

        self.directory = directory
        self.__created = False

    def _write_readme(self):
        with io.open(os.path.join(self.directory, 'README'), 'w') as readme:
            readme.write(
                'This directory is maintained by the pre-commit project.\n'
                'Learn more: https://github.com/pre-commit/pre-commit\n'
            )

    def _write_sqlite_db(self):
        # To avoid a race where someone ^Cs between db creation and execution
        # of the CREATE TABLE statement
        fd, tmpfile = tempfile.mkstemp(dir=self.directory)
        # We'll be managing this file ourselves
        os.close(fd)
        # sqlite doesn't close its fd with its contextmanager >.<
        # contextlib.closing fixes this.
        # See: http://stackoverflow.com/a/28032829/812183
        with contextlib.closing(sqlite3.connect(tmpfile)) as db:
            db.executescript(
                'CREATE TABLE repos ('
                '    repo CHAR(255) NOT NULL,'
                '    ref CHAR(255) NOT NULL,'
                '    path CHAR(255) NOT NULL,'
                '    PRIMARY KEY (repo, ref)'
                ');'
            )

        # Atomic file move
        os.rename(tmpfile, self.db_path)

    def _create(self):
        if os.path.exists(self.db_path):
            return
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
            self._write_readme()
        self._write_sqlite_db()

    def require_created(self):
        """Require the pre-commit file store to be created."""
        if self.__created:
            return

        self._create()
        self.__created = True

    def clone(self, url, sha):
        """Clone the given url and checkout the specific sha."""
        self.require_created()

        # Check if we already exist
        with sqlite3.connect(self.db_path) as db:
            result = db.execute(
                'SELECT path FROM repos WHERE repo = ? AND ref = ?',
                [url, sha],
            ).fetchone()
            if result:
                return result[0]

        logger.info('Initializing environment for {0}.'.format(url))

        dir = tempfile.mkdtemp(prefix='repo', dir=self.directory)
        with clean_path_on_failure(dir):
            cmd_output('git', 'clone', '--no-checkout', url, dir)
            with cwd(dir):
                cmd_output('git', 'reset', sha, '--hard')

        # Update our db with the created repo
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                'INSERT INTO repos (repo, ref, path) VALUES (?, ?, ?)',
                [url, sha, dir],
            )
        return dir

    def get_repo_path_getter(self, repo, sha):
        return self.RepoPathGetter(repo, sha, self)

    @cached_property
    def cmd_runner(self):
        return PrefixedCommandRunner(self.directory)

    @cached_property
    def db_path(self):
        return os.path.join(self.directory, 'db.db')
