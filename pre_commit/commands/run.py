from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import sys

from pre_commit import color
from pre_commit import git
from pre_commit.logging_handler import LoggingHandler
from pre_commit.output import get_hook_message
from pre_commit.output import sys_stdout_write_wrapper
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import cmd_output
from pre_commit.util import noop_context


logger = logging.getLogger('pre_commit')


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


def get_changed_files(new, old):
    return cmd_output(
        'git', 'diff', '--name-only', '{0}..{1}'.format(old, new),
    )[1].splitlines()


def get_filenames(args, include_expr, exclude_expr):
    if args.origin and args.source:
        getter = git.get_files_matching(
            lambda: get_changed_files(args.origin, args.source),
        )
    elif args.files:
        getter = git.get_files_matching(lambda: args.files)
    elif args.all_files:
        getter = git.get_all_files_matching
    elif git.is_in_merge_conflict():
        getter = git.get_conflicted_files_matching
    else:
        getter = git.get_staged_files_matching
    return getter(include_expr, exclude_expr)


def _run_single_hook(hook, repo, args, write, skips=frozenset()):
    filenames = get_filenames(args, hook['files'], hook['exclude'])
    if hook['id'] in skips:
        _print_user_skipped(hook, write, args)
        return 0
    elif not filenames and not hook['always_run']:
        _print_no_files_skipped(hook, write, args)
        return 0

    # Print the hook and the dots first in case the hook takes hella long to
    # run.
    write(get_hook_message(_hook_msg_start(hook, args.verbose), end_len=6))
    sys.stdout.flush()

    diff_before = cmd_output('git', 'diff', retcode=None, encoding=None)
    retcode, stdout, stderr = repo.run_hook(hook, tuple(filenames))
    diff_after = cmd_output('git', 'diff', retcode=None, encoding=None)

    file_modifications = diff_before != diff_after

    # If the hook makes changes, fail the commit
    if file_modifications:
        retcode = 1

    if retcode:
        retcode = 1
        print_color = color.RED
        pass_fail = 'Failed'
    else:
        retcode = 0
        print_color = color.GREEN
        pass_fail = 'Passed'

    write(color.format_color(pass_fail, print_color, args.color) + '\n')

    if (stdout or stderr or file_modifications) and (retcode or args.verbose):
        write('hookid: {0}\n'.format(hook['id']))
        write('\n')

        # Print a message if failing due to file modifications
        if file_modifications:
            write('Files were modified by this hook.')

            if stdout or stderr:
                write(' Additional output:\n')

            write('\n')

        for output in (stdout, stderr):
            assert type(output) is bytes, type(output)
            if output.strip():
                write(output.strip() + b'\n')
        write('\n')

    return retcode


def _run_hooks(repo_hooks, args, write, environ):
    """Actually run the hooks."""
    skips = _get_skips(environ)
    retval = 0
    for repo, hook in repo_hooks:
        retval |= _run_single_hook(hook, repo, args, write, skips)
    return retval


def get_repo_hooks(runner):
    for repo in runner.repositories:
        for _, hook in repo.hooks:
            yield (repo, hook)


def _has_unmerged_paths(runner):
    _, stdout, _ = runner.cmd_runner.run(['git', 'ls-files', '--unmerged'])
    return bool(stdout.strip())


def _has_unstaged_config(runner):
    retcode, _, _ = runner.cmd_runner.run(
        ('git', 'diff', '--exit-code', runner.config_file_path),
        retcode=None,
    )
    # be explicit, other git errors don't mean it has an unstaged config.
    return retcode == 1


def run(runner, args, write=sys_stdout_write_wrapper, environ=os.environ):
    no_stash = args.no_stash or args.all_files or bool(args.files)
    # Set up our logging handler
    logger.addHandler(LoggingHandler(args.color, write=write))
    logger.setLevel(logging.INFO)

    # Check if we have unresolved merge conflict files and fail fast.
    if _has_unmerged_paths(runner):
        logger.error('Unmerged files.  Resolve before committing.')
        return 1
    if bool(args.source) != bool(args.origin):
        logger.error('Specify both --origin and --source.')
        return 1
    if _has_unstaged_config(runner) and not no_stash:
        if args.allow_unstaged_config:
            logger.warn(
                'You have an unstaged config file and have specified the '
                '--allow-unstaged-config option.\n'
                'Note that your config will be stashed before the config is '
                'parsed unless --no-stash is specified.',
            )
        else:
            logger.error(
                'Your .pre-commit-config.yaml is unstaged.\n'
                '`git add .pre-commit-config.yaml` to fix this.\n'
                'Run pre-commit with --allow-unstaged-config to silence this.'
            )
            return 1

    if no_stash:
        ctx = noop_context()
    else:
        ctx = staged_files_only(runner.cmd_runner)

    with ctx:
        repo_hooks = list(get_repo_hooks(runner))

        if args.hook:
            repo_hooks = [
                (repo, hook) for repo, hook in repo_hooks
                if hook['id'] == args.hook
            ]
            if not repo_hooks:
                write('No hook with id `{0}`\n'.format(args.hook))
                return 1

        # Filter hooks for stages
        repo_hooks = [
            (repo, hook) for repo, hook in repo_hooks
            if not hook['stages'] or args.hook_stage in hook['stages']
        ]

        return _run_hooks(repo_hooks, args, write, environ)
