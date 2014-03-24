
from __future__ import print_function

import os
import pkg_resources
import stat
from plumbum import local

from pre_commit.ordereddict import OrderedDict
from pre_commit.repository import Repository


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
    pass
