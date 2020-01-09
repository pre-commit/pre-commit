import collections
import json
import logging
import os
import shlex

import pre_commit.constants as C
from pre_commit import five
from pre_commit.clientlib import load_manifest
from pre_commit.clientlib import LOCAL
from pre_commit.clientlib import MANIFEST_HOOK_DICT
from pre_commit.clientlib import META
from pre_commit.languages.all import languages
from pre_commit.languages.helpers import environment_dir
from pre_commit.prefix import Prefix
from pre_commit.util import parse_version
from pre_commit.util import rmtree


logger = logging.getLogger('pre_commit')


def _state(additional_deps):
    return {'additional_dependencies': sorted(additional_deps)}


def _state_filename(prefix, venv):
    return prefix.path(venv, '.install_state_v' + C.INSTALLED_STATE_VERSION)


def _read_state(prefix, venv):
    filename = _state_filename(prefix, venv)
    if not os.path.exists(filename):
        return None
    else:
        with open(filename) as f:
            return json.load(f)


def _write_state(prefix, venv, state):
    state_filename = _state_filename(prefix, venv)
    staging = state_filename + 'staging'
    with open(staging, 'w') as state_file:
        state_file.write(five.to_text(json.dumps(state)))
    # Move the file into place atomically to indicate we've installed
    os.rename(staging, state_filename)


_KEYS = tuple(item.key for item in MANIFEST_HOOK_DICT.items)


class Hook(collections.namedtuple('Hook', ('src', 'prefix') + _KEYS)):
    __slots__ = ()

    @property
    def cmd(self):
        return tuple(shlex.split(self.entry)) + tuple(self.args)

    @property
    def install_key(self):
        return (
            self.prefix,
            self.language,
            self.language_version,
            tuple(self.additional_dependencies),
        )

    def installed(self):
        lang = languages[self.language]
        venv = environment_dir(lang.ENVIRONMENT_DIR, self.language_version)
        return (
            venv is None or (
                (
                    _read_state(self.prefix, venv) ==
                    _state(self.additional_dependencies)
                ) and
                lang.healthy(self.prefix, self.language_version)
            )
        )

    def install(self):
        logger.info(f'Installing environment for {self.src}.')
        logger.info('Once installed this environment will be reused.')
        logger.info('This may take a few minutes...')

        lang = languages[self.language]
        venv = environment_dir(lang.ENVIRONMENT_DIR, self.language_version)

        # There's potentially incomplete cleanup from previous runs
        # Clean it up!
        if self.prefix.exists(venv):
            rmtree(self.prefix.path(venv))

        lang.install_environment(
            self.prefix, self.language_version, self.additional_dependencies,
        )
        # Write our state to indicate we're installed
        _write_state(self.prefix, venv, _state(self.additional_dependencies))

    def run(self, file_args, color):
        lang = languages[self.language]
        return lang.run_hook(self, file_args, color)

    @classmethod
    def create(cls, src, prefix, dct):
        # TODO: have cfgv do this (?)
        extra_keys = set(dct) - set(_KEYS)
        if extra_keys:
            logger.warning(
                'Unexpected key(s) present on {} => {}: '
                '{}'.format(src, dct['id'], ', '.join(sorted(extra_keys))),
            )
        return cls(src=src, prefix=prefix, **{k: dct[k] for k in _KEYS})


def _hook(*hook_dicts, **kwargs):
    root_config = kwargs.pop('root_config')
    assert not kwargs, kwargs
    ret, rest = dict(hook_dicts[0]), hook_dicts[1:]
    for dct in rest:
        ret.update(dct)

    version = ret['minimum_pre_commit_version']
    if parse_version(version) > parse_version(C.VERSION):
        logger.error(
            'The hook `{}` requires pre-commit version {} but version {} '
            'is installed.  '
            'Perhaps run `pip install --upgrade pre-commit`.'.format(
                ret['id'], version, C.VERSION,
            ),
        )
        exit(1)

    lang = ret['language']
    if ret['language_version'] == C.DEFAULT:
        ret['language_version'] = root_config['default_language_version'][lang]
    if ret['language_version'] == C.DEFAULT:
        ret['language_version'] = languages[lang].get_default_version()

    if not ret['stages']:
        ret['stages'] = root_config['default_stages']

    return ret


def _non_cloned_repository_hooks(repo_config, store, root_config):
    def _prefix(language_name, deps):
        language = languages[language_name]
        # pygrep / script / system / docker_image do not have
        # environments so they work out of the current directory
        if language.ENVIRONMENT_DIR is None:
            return Prefix(os.getcwd())
        else:
            return Prefix(store.make_local(deps))

    return tuple(
        Hook.create(
            repo_config['repo'],
            _prefix(hook['language'], hook['additional_dependencies']),
            _hook(hook, root_config=root_config),
        )
        for hook in repo_config['hooks']
    )


def _cloned_repository_hooks(repo_config, store, root_config):
    repo, rev = repo_config['repo'], repo_config['rev']
    manifest_path = os.path.join(store.clone(repo, rev), C.MANIFEST_FILE)
    by_id = {hook['id']: hook for hook in load_manifest(manifest_path)}

    for hook in repo_config['hooks']:
        if hook['id'] not in by_id:
            logger.error(
                '`{}` is not present in repository {}.  '
                'Typo? Perhaps it is introduced in a newer version?  '
                'Often `pre-commit autoupdate` fixes this.'
                .format(hook['id'], repo),
            )
            exit(1)

    hook_dcts = [
        _hook(by_id[hook['id']], hook, root_config=root_config)
        for hook in repo_config['hooks']
    ]
    return tuple(
        Hook.create(
            repo_config['repo'],
            Prefix(store.clone(repo, rev, hook['additional_dependencies'])),
            hook,
        )
        for hook in hook_dcts
    )


def _repository_hooks(repo_config, store, root_config):
    if repo_config['repo'] in {LOCAL, META}:
        return _non_cloned_repository_hooks(repo_config, store, root_config)
    else:
        return _cloned_repository_hooks(repo_config, store, root_config)


def install_hook_envs(hooks, store):
    def _need_installed():
        seen = set()
        ret = []
        for hook in hooks:
            if hook.install_key not in seen and not hook.installed():
                ret.append(hook)
            seen.add(hook.install_key)
        return ret

    if not _need_installed():
        return
    with store.exclusive_lock():
        # Another process may have already completed this work
        for hook in _need_installed():
            hook.install()


def all_hooks(root_config, store):
    return tuple(
        hook
        for repo in root_config['repos']
        for hook in _repository_hooks(repo, store, root_config)
    )
