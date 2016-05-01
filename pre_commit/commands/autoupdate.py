from __future__ import print_function
from __future__ import unicode_literals

import sys

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import is_local_hooks
from pre_commit.clientlib.validate_config import load_config
from pre_commit.jsonschema_extensions import remove_defaults
from pre_commit.repository import Repository
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from pre_commit.util import yaml_dump


class RepositoryCannotBeUpdatedError(RuntimeError):
    pass


def _update_repository(repo_config, runner):
    """Updates a repository to the tip of `master`.  If the repository cannot
    be updated because a hook that is configured does not exist in `master`,
    this raises a RepositoryCannotBeUpdatedError

    Args:
        repo_config - A config for a repository
    """
    repo = Repository.create(repo_config, runner.store)

    with cwd(repo.repo_path_getter.repo_path):
        cmd_output('git', 'fetch')
        head_sha = cmd_output('git', 'rev-parse', 'origin/master')[1].strip()

    # Don't bother trying to update if our sha is the same
    if head_sha == repo_config['sha']:
        return head_sha

    # Modify the sha to be the head sha
    new_config = dict(repo_config)
    new_config['sha'] = head_sha
    new_repo = Repository.create(new_config, runner.store)

    # See if any of our hooks were deleted with the new commits
    hooks = set(hook_id for hook_id, _ in repo.hooks)
    hooks_missing = hooks - (hooks & set(new_repo.manifest.hooks.keys()))
    if hooks_missing:
        raise RepositoryCannotBeUpdatedError(
            'Cannot update because the tip of master is missing these hooks:\n'
            '{0}'.format(', '.join(sorted(hooks_missing)))
        )

    return head_sha


def autoupdate(runner):
    """Auto-update the pre-commit config to the latest versions of repos."""
    retv = 0
    changed = False

    configs = load_config(runner.config_file_path)

    for repo_config in configs:
        if is_local_hooks(repo_config):
            continue
        sys.stdout.write('Updating {0}...'.format(repo_config['repo']))
        sys.stdout.flush()
        original_sha = repo_config['sha']
        try:
            new_sha = _update_repository(repo_config, runner)
        except RepositoryCannotBeUpdatedError as error:
            print(error.args[0])
            retv = 1
            continue

        if new_sha != original_sha:
            changed = True
            print('updating {0} -> {1}.'.format(original_sha, new_sha))
            repo_config['sha'] = new_sha
        else:
            print('already up to date.')

    if changed:
        with open(runner.config_file_path, 'w') as config_file:
            config_file.write(
                yaml_dump(remove_defaults(configs, CONFIG_JSON_SCHEMA))
            )

    return retv
