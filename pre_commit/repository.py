from __future__ import unicode_literals

import logging
import shutil

from cached_property import cached_property

from pre_commit import git
from pre_commit.clientlib.validate_config import is_local_hooks
from pre_commit.clientlib.validate_manifest import MANIFEST_JSON_SCHEMA
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.languages.all import languages
from pre_commit.languages.helpers import environment_dir
from pre_commit.manifest import Manifest
from pre_commit.prefixed_command_runner import PrefixedCommandRunner


logger = logging.getLogger('pre_commit')


class Repository(object):
    def __init__(self, repo_config, repo_path_getter):
        self.repo_config = repo_config
        self.repo_path_getter = repo_path_getter
        self.__installed = False

    @classmethod
    def create(cls, config, store):
        if is_local_hooks(config):
            return LocalRepository(config)
        else:
            repo_path_getter = store.get_repo_path_getter(
                config['repo'], config['sha']
            )
            return cls(config, repo_path_getter)

    @cached_property
    def repo_url(self):
        return self.repo_config['repo']

    @cached_property
    def sha(self):
        return self.repo_config['sha']

    @cached_property
    def languages(self):
        return set(
            (hook['language'], hook['language_version'])
            for _, hook in self.hooks
        )

    @cached_property
    def hooks(self):
        # TODO: merging in manifest dicts is a smell imo
        return tuple(
            (hook['id'], dict(self.manifest.hooks[hook['id']], **hook))
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def manifest(self):
        return Manifest(self.repo_path_getter)

    @cached_property
    def cmd_runner(self):
        return PrefixedCommandRunner(self.repo_path_getter.repo_path)

    def require_installed(self):
        if self.__installed:
            return

        self.install()
        self.__installed = True

    def install(self):
        """Install the hook repository."""
        def language_is_installed(language_name, language_version):
            language = languages[language_name]
            directory = environment_dir(
                language.ENVIRONMENT_DIR, language_version,
            )
            return (
                directory is None or
                self.cmd_runner.exists(directory, '.installed')
            )

        if not all(
            language_is_installed(language_name, language_version)
            for language_name, language_version in self.languages
        ):
            logger.info(
                'Installing environment for {0}.'.format(self.repo_url)
            )
            logger.info('Once installed this environment will be reused.')
            logger.info('This may take a few minutes...')

        for language_name, language_version in self.languages:
            language = languages[language_name]
            if language_is_installed(language_name, language_version):
                continue

            directory = environment_dir(
                language.ENVIRONMENT_DIR, language_version,
            )
            # There's potentially incomplete cleanup from previous runs
            # Clean it up!
            if self.cmd_runner.exists(directory):
                shutil.rmtree(self.cmd_runner.path(directory))

            language.install_environment(self.cmd_runner, language_version)
            # Touch the .installed file (atomic) to indicate we've installed
            open(self.cmd_runner.path(directory, '.installed'), 'w').close()

    def run_hook(self, hook, file_args):
        """Run a hook.

        Args:
            hook - Hook dictionary
            file_args - List of files to run
        """
        self.require_installed()
        return languages[hook['language']].run_hook(
            self.cmd_runner, hook, file_args,
        )


class LocalRepository(Repository):
    def __init__(self, repo_config):
        super(LocalRepository, self).__init__(repo_config, None)

    @cached_property
    def hooks(self):
        return tuple(
            (hook['id'], apply_defaults(hook, MANIFEST_JSON_SCHEMA['items']))
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def cmd_runner(self):
        return PrefixedCommandRunner(git.get_root())

    @cached_property
    def sha(self):
        raise NotImplementedError

    @cached_property
    def manifest(self):
        raise NotImplementedError
