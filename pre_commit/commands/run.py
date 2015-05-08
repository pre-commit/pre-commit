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


class HookExecutor(object):
    def __init__(self, hook, invoker):
        self.hook = hook
        self._invoker = invoker

    def invoke(self, filenames):
        return self._invoker(self.hook, filenames)


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


def _run_single_hook(hook_executor, args, write, skips=frozenset()):
    hook = hook_executor.hook
    filenames = get_filenames(args, hook['files'], hook['exclude'])
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

    retcode, stdout, stderr = hook_executor.invoke(filenames)

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


def _run_hooks(hook_executors, args, write, environ):
    """Actually run the hooks."""
    skips = _get_skips(environ)
    retval = 0
    for hook_executor in hook_executors:
        retval |= _run_single_hook(hook_executor, args, write, skips)
    return retval


def get_hook_executors(runner):
    for repo in runner.repositories:
        for _, repo_hook in repo.hooks:
            yield HookExecutor(repo_hook, repo.run_hook)


def _has_unmerged_paths(runner):
    _, stdout, _ = runner.cmd_runner.run(['git', 'ls-files', '--unmerged'])
    return bool(stdout.strip())


def run(runner, args, write=sys_stdout_write_wrapper, environ=os.environ):
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

    # Don't stash if specified or files are specified
    if args.no_stash or args.all_files or args.files:
        ctx = noop_context()
    else:
        ctx = staged_files_only(runner.cmd_runner)

    with ctx:
        hook_executors = list(get_hook_executors(runner))
        if args.hook:
            hook_executors = [
                he for he in hook_executors
                if he.hook['id'] == args.hook
            ]
            if not hook_executors:
                write('No hook with id `{0}`\n'.format(args.hook))
                return 1
        return _run_hooks(hook_executors, args, write, environ)
