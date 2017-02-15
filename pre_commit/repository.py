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


def _state(additional_deps):
    return {'additional_dependencies': sorted(additional_deps)}


def _state_filename(cmd_runner, venv):
    return cmd_runner.path(venv, '.install_state_v' + INSTALLED_STATE_VERSION)


def _read_installed_state(cmd_runner, venv):
    filename = _state_filename(cmd_runner, venv)
    if not os.path.exists(filename):
        return None
    else:
        return json.loads(io.open(filename).read())


def _write_installed_state(cmd_runner, venv, state):
    state_filename = _state_filename(cmd_runner, venv)
    staging = state_filename + 'staging'
    with io.open(staging, 'w') as state_file:
        state_file.write(five.to_text(json.dumps(state)))
    # Move the file into place atomically to indicate we've installed
    os.rename(staging, state_filename)


def _installed(cmd_runner, language_name, language_version, additional_deps):
    language = languages[language_name]
    venv = environment_dir(language.ENVIRONMENT_DIR, language_version)
    return (
        venv is None or
        _read_installed_state(cmd_runner, venv) == _state(additional_deps)
    )


def _install_all(venvs, repo_url):
    """Tuple of (cmd_runner, language, version, deps)"""
    need_installed = tuple(
        (cmd_runner, language_name, version, deps)
        for cmd_runner, language_name, version, deps in venvs
        if not _installed(cmd_runner, language_name, version, deps)
    )

    if need_installed:
        logger.info(
            'Installing environment for {}.'.format(repo_url)
        )
        logger.info('Once installed this environment will be reused.')
        logger.info('This may take a few minutes...')

    for cmd_runner, language_name, version, deps in need_installed:
        language = languages[language_name]
        venv = environment_dir(language.ENVIRONMENT_DIR, version)

        # There's potentially incomplete cleanup from previous runs
        # Clean it up!
        if cmd_runner.exists(venv):
            shutil.rmtree(cmd_runner.path(venv))

        language.install_environment(cmd_runner, version, deps)
        # Write our state to indicate we're installed
        state = _state(deps)
        _write_installed_state(cmd_runner, venv, state)


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
    def _cmd_runner(self):
        return PrefixedCommandRunner(self.repo_path_getter.repo_path)

    @cached_property
    def _venvs(self):
        deps_dict = defaultdict(_UniqueList)
        for _, hook in self.hooks:
            deps_dict[(hook['language'], hook['language_version'])].update(
                hook.get('additional_dependencies', []),
            )
        ret = []
        for (language, version), deps in deps_dict.items():
            ret.append((self._cmd_runner, language, version, deps))
        return tuple(ret)

    @cached_property
    def manifest(self):
        return Manifest(self.repo_path_getter, self.repo_config['repo'])

    @cached_property
    def hooks(self):
        for hook in self.repo_config['hooks']:
            if hook['id'] not in self.manifest.hooks:
                logger.error(
                    '`{}` is not present in repository {}.  '
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
                    'The hook `{}` requires pre-commit version {} but '
                    'version {} is installed.  '
                    'Perhaps run `pip install --upgrade pre-commit`.'.format(
                        hook['id'], hook_version, _pre_commit_version,
                    )
                )
                exit(1)
        return tuple(
            (hook['id'], dict(self.manifest.hooks[hook['id']], **hook))
            for hook in self.repo_config['hooks']
        )

    def require_installed(self):
        if not self.__installed:
            _install_all(self._venvs, self.repo_config['repo'])
            self.__installed = True

    def run_hook(self, hook, file_args):
        """Run a hook.

        Args:
            hook - Hook dictionary
            file_args - List of files to run
        """
        self.require_installed()
        return languages[hook['language']].run_hook(
            self._cmd_runner, hook, file_args,
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
    def manifest(self):
        raise NotImplementedError


class _UniqueList(list):
    def __init__(self):
        self._set = set()

    def update(self, obj):
        for item in obj:
            if item not in self._set:
                self._set.add(item)
                self.append(item)
