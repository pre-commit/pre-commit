from __future__ import unicode_literals

import io
import json
import logging
import os
import shutil
from collections import defaultdict

import pkg_resources
from cached_property import cached_property

import pre_commit.constants as C
from pre_commit import five
from pre_commit import git
from pre_commit.clientlib import is_local_repo
from pre_commit.clientlib import MANIFEST_HOOK_DICT
from pre_commit.languages.all import languages
from pre_commit.languages.helpers import environment_dir
from pre_commit.manifest import Manifest
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.schema import apply_defaults
from pre_commit.schema import validate


logger = logging.getLogger('pre_commit')


def _state(additional_deps):
    return {'additional_dependencies': sorted(additional_deps)}


def _state_filename(cmd_runner, venv):
    return cmd_runner.path(
        venv, '.install_state_v' + C.INSTALLED_STATE_VERSION,
    )


def _read_state(cmd_runner, venv):
    filename = _state_filename(cmd_runner, venv)
    if not os.path.exists(filename):
        return None
    else:
        return json.loads(io.open(filename).read())


def _write_state(cmd_runner, venv, state):
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
        venv is None or (
            _read_state(cmd_runner, venv) == _state(additional_deps) and
            language.healthy(cmd_runner, language_version)
        )
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
            'Installing environment for {}.'.format(repo_url),
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
        _write_state(cmd_runner, venv, state)


def _validate_minimum_version(hook):
    hook_version = pkg_resources.parse_version(
        hook['minimum_pre_commit_version'],
    )
    if hook_version > C.VERSION_PARSED:
        logger.error(
            'The hook `{}` requires pre-commit version {} but '
            'version {} is installed.  '
            'Perhaps run `pip install --upgrade pre-commit`.'.format(
                hook['id'], hook_version, C.VERSION_PARSED,
            ),
        )
        exit(1)
    return hook


class Repository(object):
    def __init__(self, repo_config, store):
        self.repo_config = repo_config
        self.store = store
        self.__installed = False

    @classmethod
    def create(cls, config, store):
        if is_local_repo(config):
            return LocalRepository(config, store)
        else:
            return cls(config, store)

    @cached_property
    def _repo_path(self):
        return self.store.clone(
            self.repo_config['repo'], self.repo_config['sha'],
        )

    @cached_property
    def _cmd_runner(self):
        return PrefixedCommandRunner(self._repo_path)

    def _cmd_runner_from_deps(self, language_name, deps):
        return self._cmd_runner

    @cached_property
    def manifest(self):
        return Manifest(self._repo_path, self.repo_config['repo'])

    @cached_property
    def hooks(self):
        for hook in self.repo_config['hooks']:
            if hook['id'] not in self.manifest.hooks:
                logger.error(
                    '`{}` is not present in repository {}.  '
                    'Typo? Perhaps it is introduced in a newer version?  '
                    'Often `pre-commit autoupdate` fixes this.'.format(
                        hook['id'], self.repo_config['repo'],
                    ),
                )
                exit(1)

            _validate_minimum_version(self.manifest.hooks[hook['id']])

        return tuple(
            (hook['id'], dict(self.manifest.hooks[hook['id']], **hook))
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def _venvs(self):
        deps_dict = defaultdict(_UniqueList)
        for _, hook in self.hooks:
            deps_dict[(hook['language'], hook['language_version'])].update(
                hook['additional_dependencies'],
            )
        ret = []
        for (language, version), deps in deps_dict.items():
            ret.append((self._cmd_runner, language, version, deps))
        return tuple(ret)

    def require_installed(self):
        if not self.__installed:
            _install_all(self._venvs, self.repo_config['repo'])
            self.__installed = True

    def run_hook(self, hook, file_args):
        """Run a hook.

        :param dict hook:
        :param tuple file_args: all the files to run the hook on
        """
        self.require_installed()
        language_name = hook['language']
        deps = hook['additional_dependencies']
        cmd_runner = self._cmd_runner_from_deps(language_name, deps)
        return languages[language_name].run_hook(cmd_runner, hook, file_args)


class LocalRepository(Repository):
    def _cmd_runner_from_deps(self, language_name, deps):
        """local repositories have a cmd runner per hook"""
        language = languages[language_name]
        # pcre / script / system do not have environments so they work out
        # of the current directory
        if language.ENVIRONMENT_DIR is None:
            return PrefixedCommandRunner(git.get_root())
        else:
            return PrefixedCommandRunner(self.store.make_local(deps))

    @cached_property
    def manifest(self):
        raise NotImplementedError

    @cached_property
    def hooks(self):
        return tuple(
            (
                hook['id'],
                _validate_minimum_version(
                    apply_defaults(
                        validate(hook, MANIFEST_HOOK_DICT),
                        MANIFEST_HOOK_DICT,
                    ),
                ),
            )
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def _venvs(self):
        ret = []
        for _, hook in self.hooks:
            language = hook['language']
            version = hook['language_version']
            deps = hook['additional_dependencies']
            ret.append((
                self._cmd_runner_from_deps(language, deps),
                language, version, deps,
            ))
        return tuple(ret)


class _UniqueList(list):
    def __init__(self):
        self._set = set()

    def update(self, obj):
        for item in obj:
            if item not in self._set:
                self._set.add(item)
                self.append(item)
