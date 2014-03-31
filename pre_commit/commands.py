
from __future__ import print_function

import os
import pkg_resources
import shutil
import stat
from plumbum import local

import pre_commit.constants as C
from pre_commit.clientlib.validate_config import load_config
from pre_commit.ordereddict import OrderedDict
from pre_commit.repository import Repository
from pre_commit.yaml_extensions import ordered_dump
from pre_commit.yaml_extensions import ordered_load


def install(runner):
    """Install the pre-commit hooks."""
    pre_commit_file = pkg_resources.resource_filename('pre_commit', 'resources/pre-commit.sh')
    with open(runner.pre_commit_path, 'w') as pre_commit_file_obj:
        pre_commit_file_obj.write(open(pre_commit_file).read())

    original_mode = os.stat(runner.pre_commit_path).st_mode
    os.chmod(
        runner.pre_commit_path,
        original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    print('pre-commit installed at {0}'.format(runner.pre_commit_path))

    return 0


def uninstall(runner):
    """Uninstall the pre-commit hooks."""
    if os.path.exists(runner.pre_commit_path):
        os.remove(runner.pre_commit_path)
        print('pre-commit uninstalled')
    return 0


class RepositoryCannotBeUpdatedError(RuntimeError): pass


def _update_repository(repo_config):
    """Updates a repository to the tip of `master`.  If the repository cannot
    be updated because a hook that is configured does not exist in `master`,
    this raises a RepositoryCannotBeUpdatedError

    Args:
        repo_config - A config for a repository
    """
    repo = Repository(repo_config)

    with repo.in_checkout():
        local['git']['fetch']()
        head_sha = local['git']['rev-parse', 'origin/master']().strip()

    # Don't bother trying to update if our sha is the same
    if head_sha == repo_config['sha']:
        return repo_config

    # Construct a new config with the head sha
    new_config = OrderedDict(repo_config)
    new_config['sha'] = head_sha
    new_repo = Repository(new_config)

    # See if any of our hooks were deleted with the new commits
    hooks = set(repo.hooks.keys())
    hooks_missing = hooks - (hooks & set(new_repo.manifest.keys()))
    if hooks_missing:
        raise RepositoryCannotBeUpdatedError(
            'Cannot update because the tip of master is missing these hooks:\n'
            '{0}'.format(', '.join(sorted(hooks_missing)))
        )

    return new_config


def autoupdate(runner):
    """Auto-update the pre-commit config to the latest versions of repos."""
    retv = 0
    output_configs = []
    changed = False

    input_configs = load_config(
        runner.config_file_path,
        load_strategy=ordered_load,
    )

    for repo_config in input_configs:
        print('Updating {0}...'.format(repo_config['repo']), end='')
        try:
            new_repo_config = _update_repository(repo_config)
        except RepositoryCannotBeUpdatedError as e:
            print(e.args[0])
            output_configs.append(repo_config)
            retv = 1
            continue

        if new_repo_config['sha'] != repo_config['sha']:
            changed = True
            print(
                'updating {0} -> {1}.'.format(
                    repo_config['sha'], new_repo_config['sha'],
                )
            )
            output_configs.append(new_repo_config)
        else:
            print('already up to date.')
            output_configs.append(repo_config)

    if changed:
        with open(runner.config_file_path, 'w') as config_file:
            config_file.write(
                ordered_dump(output_configs, **C.YAML_DUMP_KWARGS)
            )

    return retv


def clean(runner):
    if os.path.exists(runner.hooks_workspace_path):
        shutil.rmtree(runner.hooks_workspace_path)
        print('Cleaned {0}.'.format(runner.hooks_workspace_path))
    return 0
