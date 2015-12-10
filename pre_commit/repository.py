from __future__ import unicode_literals

import io
import json
import logging
import os
import shutil
from collections import defaultdict

import pkg_resources
from cached_property import cached_property

from pre_commit import five
from pre_commit import git
from pre_commit.clientlib.validate_config import is_local_hooks
from pre_commit.clientlib.validate_manifest import MANIFEST_JSON_SCHEMA
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.languages.all import languages
from pre_commit.languages.helpers import environment_dir
from pre_commit.manifest import Manifest
from pre_commit.prefixed_command_runner import PrefixedCommandRunner


logger = logging.getLogger('pre_commit')

_pre_commit_version = pkg_resources.parse_version(
    pkg_resources.get_distribution('pre-commit').version
)

# Bump when installation changes in a backwards / forwards incompatible way
INSTALLED_STATE_VERSION = '1'


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
    def additional_dependencies(self):
        dep_dict = defaultdict(lambda: defaultdict(set))
        for _, hook in self.hooks:
            dep_dict[hook['language']][hook['language_version']].update(
                hook.get('additional_dependencies', []),
            )
        return dep_dict

    @cached_property
    def hooks(self):
        for hook in self.repo_config['hooks']:
            if hook['id'] not in self.manifest.hooks:
                logger.error(
                    '`{0}` is not present in repository {1}.  '
                    'Typo? Perhaps it is introduced in a newer version?  '
                    'Often `pre-commit autoupdate` fixes this.'.format(
                        hook['id'], self.repo_config['repo'],
                    )
                )
                exit(1)
            hook_version = pkg_resources.parse_version(
                self.manifest.hooks[hook['id']]['minimum_pre_commit_version'],
            )
            if hook_version > _pre_commit_version:
                logger.error(
                    'The hook `{0}` requires pre-commit version {1} but '
                    'version {2} is installed.  '
                    'Perhaps run `pip install --upgrade pre-commit`.'.format(
                        hook['id'], hook_version, _pre_commit_version,
                    )
                )
                exit(1)
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
        def state(language_name, language_version):
            return {
                'additional_dependencies': sorted(
                    self.additional_dependencies[
                        language_name
                    ][language_version],
                )
            }

        def state_filename(venv, suffix=''):
            return self.cmd_runner.path(
                venv, '.install_state_v' + INSTALLED_STATE_VERSION + suffix,
            )

        def read_state(venv):
            if not os.path.exists(state_filename(venv)):
                return None
            else:
                return json.loads(io.open(state_filename(venv)).read())

        def write_state(venv, language_name, language_version):
            with io.open(
                    state_filename(venv, suffix='staging'), 'w',
            ) as state_file:
                state_file.write(five.to_text(json.dumps(
                    state(language_name, language_version),
                )))
            # Move the file into place atomically to indicate we've installed
            os.rename(
                state_filename(venv, suffix='staging'),
                state_filename(venv),
            )

        def language_is_installed(language_name, language_version):
            language = languages[language_name]
            venv = environment_dir(language.ENVIRONMENT_DIR, language_version)
            return (
                venv is None or
                read_state(venv) == state(language_name, language_version)
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
            if language_is_installed(language_name, language_version):
                continue

            language = languages[language_name]
            venv = environment_dir(language.ENVIRONMENT_DIR, language_version)

            # There's potentially incomplete cleanup from previous runs
            # Clean it up!
            if self.cmd_runner.exists(venv):
                shutil.rmtree(self.cmd_runner.path(venv))

            language.install_environment(
                self.cmd_runner, language_version,
                self.additional_dependencies[language_name][language_version],
            )
            # Write our state to indicate we're installed
            write_state(venv, language_name, language_version)

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
