
from __future__ import print_function

import argparse
import logging
import subprocess
import sys

from pre_commit import color
from pre_commit import commands
from pre_commit import git
from pre_commit.logging_handler import LoggingHandler
from pre_commit.runner import Runner
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import entry


logger = logging.getLogger('pre_commit')

COLS = int(subprocess.Popen(['tput', 'cols'], stdout=subprocess.PIPE).communicate()[0])

PASS_FAIL_LENGTH = 6


def _run_single_hook(runner, repository, hook_id, args):
    if args.all_files:
        get_filenames = git.get_all_files_matching
    else:
        get_filenames = git.get_staged_files_matching

    hook = repository.hooks[hook_id]

    # Print the hook and the dots first in case the hook takes hella long to
    # run.
    print(
        '{0}{1}'.format(
            hook['name'],
            '.' * (COLS - len(hook['name']) - PASS_FAIL_LENGTH - 6),
        ),
        end='',
    )

    retcode, stdout, stderr = repository.run_hook(
        runner.cmd_runner,
        hook_id,
        get_filenames(hook['files'], hook['exclude']),
    )

    output = '\n'.join([stdout, stderr]).strip()
    if retcode != repository.hooks[hook_id]['expected_return_value']:
        retcode = 1
        print_color = color.RED
        pass_fail = 'Failed'
    else:
        retcode = 0
        print_color = color.GREEN
        pass_fail = 'Passed'


    print(color.format_color(pass_fail, print_color, args.color))

    if output and (retcode or args.verbose):
        print('\n' + output)

    return retcode


def run_hooks(runner, args):
    """Actually run the hooks."""
    retval = 0

    for repo in runner.repositories:
        for hook_id in repo.hooks:
            retval |= _run_single_hook(runner, repo, hook_id, args)

    return retval


def run_single_hook(runner, hook_id, args):
    for repo in runner.repositories:
        if hook_id in repo.hooks:
            return _run_single_hook(runner, repo, hook_id, args)
    else:
        print('No hook with id `{0}`'.format(hook_id))
        return 1


def _run(runner, args):
    # Set up our logging handler
    logger.addHandler(LoggingHandler(args.color))
    logger.setLevel(logging.INFO)

    with staged_files_only(runner.cmd_runner):
        if args.hook:
            return run_single_hook(runner, args.hook, args)
        else:
            return run_hooks(runner, args)


@entry
def run(argv):
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('install', help='Intall the pre-commit script.')

    subparsers.add_parser('uninstall', help='Uninstall the pre-commit script.')

    subparsers.add_parser('clean', help='Clean out pre-commit files.')

    subparsers.add_parser('autoupdate', help='Auto-update hooks config.')

    run = subparsers.add_parser('run', help='Run hooks.')
    run.add_argument('hook', nargs='?', help='A single hook-id to run'),
    run.add_argument(
        '--all-files', '-a', action='store_true', default=False,
        help='Run on all the files in the repo.',
    )
    run.add_argument('--verbose', '-v', action='store_true', default=False)
    run.add_argument(
        '--color', default='auto', type=color.use_color,
        help='Whether to use color in output.  Defaults to `auto`',
    )

    help = subparsers.add_parser('help', help='Show help for a specific command.')
    help.add_argument('help_cmd', nargs='?', help='Command to show help for.')

    # Argparse doesn't really provide a way to use a `default` subparser
    if len(argv) == 0:
        argv = ['run']
    args = parser.parse_args(argv)

    runner = Runner.create()

    if args.command == 'install':
        return commands.install(runner)
    elif args.command == 'uninstall':
        return commands.uninstall(runner)
    elif args.command == 'clean':
        return commands.clean(runner)
    elif args.command == 'autoupdate':
        return commands.autoupdate(runner)
    elif args.command == 'run':
        return _run(runner, args)
    elif args.command == 'help':
        if args.help_cmd:
            parser.parse_args([args.help_cmd, '--help'])
        else:
            parser.parse_args(['--help'])
    else:
        raise NotImplementedError(
            'Command {0} not implemented.'.format(args.command)
        )

    raise AssertionError(
        'Command {0} failed to exit with a returncode'.format(args.command)
    )


if __name__ == '__main__':
    sys.exit(run())
