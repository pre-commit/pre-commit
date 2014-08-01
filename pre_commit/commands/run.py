from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import sys

from pre_commit import git
from pre_commit import color
from pre_commit.logging_handler import LoggingHandler
from pre_commit.output import get_hook_message
from pre_commit.staged_files_only import staged_files_only
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


def _run_single_hook(runner, repository, hook, args, write, skips=set()):
    if args.all_files:
        get_filenames = git.get_all_files_matching
    elif git.is_in_merge_conflict():
        get_filenames = git.get_conflicted_files_matching
    else:
        get_filenames = git.get_staged_files_matching

    filenames = get_filenames(hook['files'], hook['exclude'])
    if hook['id'] in skips:
        _print_user_skipped(hook, write, args)
        return 0
    elif not filenames:
        _print_no_files_skipped(hook, write, args)
        return 0

    # Print the hook and the dots first in case the hook takes hella long to
    # run.
    write(get_hook_message(_hook_msg_start(hook, args.verbose), end_len=6))
    sys.stdout.flush()

    retcode, stdout, stderr = repository.run_hook(hook, filenames)

    if retcode != hook['expected_return_value']:
        retcode = 1
        print_color = color.RED
        pass_fail = 'Failed'
    else:
        retcode = 0
        print_color = color.GREEN
        pass_fail = 'Passed'

    write(color.format_color(pass_fail, print_color, args.color) + '\n')

    if (stdout or stderr) and (retcode or args.verbose):
        write('hookid: {0}\n'.format(hook['id']))
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
        for _, hook in repo.hooks:
            retval |= _run_single_hook(
                runner, repo, hook, args, write, skips=skips,
            )

    return retval


def _run_hook(runner, args, write):
    hook_id = args.hook
    for repo in runner.repositories:
        for hook_id_in_repo, hook in repo.hooks:
            if hook_id == hook_id_in_repo:
                return _run_single_hook(
                    runner, repo, hook, args, write=write,
                )
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
