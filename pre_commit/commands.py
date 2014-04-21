from __future__ import print_function

import logging
import os
import pkg_resources
import shutil
import stat
import sys
from asottile.ordereddict import OrderedDict
from asottile.yaml import ordered_dump
from asottile.yaml import ordered_load
from plumbum import local

import pre_commit.constants as C
from pre_commit import git
from pre_commit import color
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import load_config
from pre_commit.jsonschema_extensions import remove_defaults
from pre_commit.logging_handler import LoggingHandler
from pre_commit.output import get_hook_message
from pre_commit.repository import Repository
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import noop_context


logger = logging.getLogger('pre_commit')


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

    with local.cwd(repo.repo_path_getter.repo_path):
        local['git']['fetch']()
        head_sha = local['git']['rev-parse', 'origin/master']().strip()

    # Don't bother trying to update if our sha is the same
    if head_sha == repo_config['sha']:
        return repo_config

    # Construct a new config with the head sha
    new_config = OrderedDict(repo_config)
    new_config['sha'] = head_sha
    new_repo = Repository.create(new_config, runner.store)

    # See if any of our hooks were deleted with the new commits
    hooks = set(repo.hooks.keys())
    hooks_missing = hooks - (hooks & set(new_repo.manifest.hooks.keys()))
    if hooks_missing:
        raise RepositoryCannotBeUpdatedError(
            'Cannot update because the tip of master is missing these hooks:\n'
            '{0}'.format(', '.join(sorted(hooks_missing)))
        )

    return remove_defaults([new_config], CONFIG_JSON_SCHEMA)[0]


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
        sys.stdout.write('Updating {0}...'.format(repo_config['repo']))
        sys.stdout.flush()
        try:
            new_repo_config = _update_repository(repo_config, runner)
        except RepositoryCannotBeUpdatedError as error:
            print(error.args[0])
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
    if os.path.exists(runner.store.directory):
        shutil.rmtree(runner.store.directory)
        print('Cleaned {0}.'.format(runner.store.directory))
    return 0


def _get_skips(environ):
    skips = environ.get('SKIP', '')
    return set(skip.strip() for skip in skips.split(',') if skip.strip())


def _hook_msg_start(hook, verbose):
    return '{0}{1}'.format(
        '[{0}] '.format(hook['id']) if verbose else '',
        hook['name'],
    )


def _print_no_files_skipped(hook, write, args):
    write(get_hook_message(
        _hook_msg_start(hook, args.verbose),
        postfix='(no files to check) ',
        end_msg='Skipped',
        end_color=color.TURQUOISE,
        use_color=args.color,
    ))


def _print_user_skipped(hook, write, args):
    write(get_hook_message(
        _hook_msg_start(hook, args.verbose),
        end_msg='Skipped',
        end_color=color.YELLOW,
        use_color=args.color,
    ))


def _run_single_hook(runner, repository, hook_id, args, write, skips=set()):
    if args.all_files:
        get_filenames = git.get_all_files_matching
    elif git.is_in_merge_conflict():
        get_filenames = git.get_conflicted_files_matching
    else:
        get_filenames = git.get_staged_files_matching

    hook = repository.hooks[hook_id]

    filenames = get_filenames(hook['files'], hook['exclude'])
    if hook_id in skips:
        _print_user_skipped(hook, write, args)
        return 0
    elif not filenames:
        _print_no_files_skipped(hook, write, args)
        return 0

    # Print the hook and the dots first in case the hook takes hella long to
    # run.
    write(get_hook_message(_hook_msg_start(hook, args.verbose), end_len=6))
    sys.stdout.flush()

    retcode, stdout, stderr = repository.run_hook(
        runner.cmd_runner,
        hook_id,
        filenames,
    )

    if retcode != repository.hooks[hook_id]['expected_return_value']:
        retcode = 1
        print_color = color.RED
        pass_fail = 'Failed'
    else:
        retcode = 0
        print_color = color.GREEN
        pass_fail = 'Passed'

    write(color.format_color(pass_fail, print_color, args.color) + '\n')

    if (stdout or stderr) and (retcode or args.verbose):
        write('\n')
        for output in (stdout, stderr):
            if output.strip():
                write(output.strip() + '\n')
        write('\n')

    return retcode


def _run_hooks(runner, args, write, environ):
    """Actually run the hooks."""
    retval = 0

    skips = _get_skips(environ)

    for repo in runner.repositories:
        for hook_id in repo.hooks:
            retval |= _run_single_hook(
                runner, repo, hook_id, args, write, skips=skips,
            )

    return retval


def _run_hook(runner, args, write):
    hook_id = args.hook
    for repo in runner.repositories:
        if hook_id in repo.hooks:
            return _run_single_hook(runner, repo, hook_id, args, write=write)
    else:
        write('No hook with id `{0}`\n'.format(hook_id))
        return 1


def _has_unmerged_paths(runner):
    _, stdout, _ = runner.cmd_runner.run(['git', 'ls-files', '--unmerged'])
    return bool(stdout.strip())


def run(runner, args, write=sys.stdout.write, environ=os.environ):
    # Set up our logging handler
    logger.addHandler(LoggingHandler(args.color, write=write))
    logger.setLevel(logging.INFO)

    # Check if we have unresolved merge conflict files and fail fast.
    if _has_unmerged_paths(runner):
        logger.error('Unmerged files.  Resolve before committing.')
        return 1

    if args.no_stash or args.all_files:
        ctx = noop_context()
    else:
        ctx = staged_files_only(runner.cmd_runner)

    with ctx:
        if args.hook:
            return _run_hook(runner, args, write=write)
        else:
            return _run_hooks(runner, args, write=write, environ=environ)
