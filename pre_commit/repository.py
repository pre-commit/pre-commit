from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Sequence
from typing import Any

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.all_languages import languages
from pre_commit.clientlib import LOCAL
from pre_commit.clientlib import META
from pre_commit.hook import Hook
from pre_commit.hook import InstallKey
from pre_commit.prefix import Prefix
from pre_commit.store import Store
from pre_commit.util import clean_path_on_failure


logger = logging.getLogger('pre_commit')


def _state_filename_v5(d: str) -> str:
    return os.path.join(d, '.pre-commit-state-v5')


def _hook_install(hook: Hook, store: Store) -> None:
    logger.info(f'Installing environment for {hook.repo}.')
    logger.info('Once installed this environment will be reused.')
    logger.info('This may take a few minutes...')

    lang = languages[hook.language]

    clone = store.clone(hook.repo, hook.rev)
    dest = tempfile.mkdtemp(prefix='i-', dir=store.directory)

    with clean_path_on_failure(dest):
        prefix = Prefix(dest)
        lang.install_environment(
            Prefix(clone), prefix,
            hook.language_version, hook.additional_dependencies,
        )
        health_error = lang.health_check(prefix, hook.language_version)
        if health_error:
            raise AssertionError(
                f'BUG: expected environment for {hook.language} to be healthy '
                f'immediately after install, please open an issue describing '
                f'your environment\n\n'
                f'more info:\n\n{health_error}',
            )

        # TODO: need more info?
        open(_state_filename_v5(dest), 'a+').close()


def _hook_installed(hook: Hook, store: Store) -> bool:
    return False


def _hook(
        *hook_dicts: dict[str, Any],
        root_config: dict[str, Any],
) -> dict[str, Any]:
    ret, rest = dict(hook_dicts[0]), hook_dicts[1:]
    for dct in rest:
        ret.update(dct)

    lang = ret['language']
    if ret['language_version'] == C.DEFAULT:
        ret['language_version'] = root_config['default_language_version'][lang]
    if ret['language_version'] == C.DEFAULT:
        ret['language_version'] = languages[lang].get_default_version()

    if not ret['stages']:
        ret['stages'] = root_config['default_stages']

    if languages[lang].install_environment is lang_base.no_install:
        if ret['language_version'] != C.DEFAULT:
            logger.error(
                f'The hook `{ret["id"]}` specifies `language_version` but is '
                f'using language `{lang}` which does not install an '
                f'environment.  '
                f'Perhaps you meant to use a specific language?',
            )
            raise SystemExit(1)
        if ret['additional_dependencies']:
            logger.error(
                f'The hook `{ret["id"]}` specifies `additional_dependencies` '
                f'but is using language `{lang}` which does not install an '
                f'environment.  '
                f'Perhaps you meant to use a specific language?',
            )
            raise SystemExit(1)

    return ret


def _repository_hooks(
        repo_config: dict[str, Any],
        store: Store,
        root_config: dict[str, Any],
) -> tuple[Hook, ...]:
    repo = repo_config['repo']
    if repo == META:
        return tuple(
            Hook.create(
                repo, '',
                _hook(hook, root_config=root_config),
            )
            for hook in repo_config['hooks']
        )
    elif repo == LOCAL:
        return tuple(
            Hook.create(
                repo, C.LOCAL_REPO_VERSION,
                _hook(hook, root_config=root_config),
            )
            for hook in repo_config['hooks']
        )
    else:
        rev = repo_config['rev']
        by_id = store.manifest(repo, rev)['hooks']

        for hook in repo_config['hooks']:
            if hook['id'] not in by_id:
                logger.error(
                    f'`{hook["id"]}` is not present in repository {repo}.  '
                    f'Typo? Perhaps it is introduced in a newer version?  '
                    f'Often `pre-commit autoupdate` fixes this.',
                )
                raise SystemExit(1)

        return tuple(
            Hook.create(
                repo, rev,
                _hook(by_id[hook['id']], hook, root_config=root_config),
            )
            for hook in repo_config['hooks']
        )


def install_hook_envs(hooks: Sequence[Hook], store: Store) -> None:
    def _need_installed() -> list[Hook]:
        seen: set[InstallKey] = set()
        ret = []
        for hook in hooks:
            key = hook.install_key
            if key not in seen and not _hook_installed(hook, store):
                ret.append(hook)
            seen.add(key)
        return ret

    if not _need_installed():
        return
    with store.exclusive_lock():
        # Another process may have already completed this work
        for hook in _need_installed():
            _hook_install(hook, store)


def all_hooks(root_config: dict[str, Any], store: Store) -> tuple[Hook, ...]:
    return tuple(
        hook
        for repo in root_config['repos']
        for hook in _repository_hooks(repo, store, root_config)
    )
