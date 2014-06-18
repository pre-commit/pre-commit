from __future__ import unicode_literals

import io
import logging
import os
import os.path
import tempfile
from cached_property import cached_property
from plumbum import local

from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.util import clean_path_on_failure
from pre_commit.util import hex_md5


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
        os.path.join(os.environ['HOME'], '.pre-commit'),
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

    def _create(self):
        if os.path.exists(self.directory):
            return
        os.makedirs(self.directory)
        self._write_readme()

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
        sha_path = os.path.join(self.directory, sha + '_' + hex_md5(url))
        if os.path.exists(sha_path):
            return os.readlink(sha_path)

        logger.info('Installing environment for {0}.'.format(url))
        logger.info('Once installed this environment will be reused.')
        logger.info('This may take a few minutes...')

        dir = tempfile.mkdtemp(prefix='repo', dir=self.directory)
        with clean_path_on_failure(dir):
            local['git']('clone', '--no-checkout', url, dir)
            with local.cwd(dir):
                local['git']('checkout', sha)

        # Make a symlink from sha->repo
        os.symlink(dir, sha_path)
        return dir

    def get_repo_path_getter(self, repo, sha):
        return self.RepoPathGetter(repo, sha, self)

    @cached_property
    def cmd_runner(self):
        return PrefixedCommandRunner(self.directory)
