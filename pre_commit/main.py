from __future__ import unicode_literals

import argparse
import pkg_resources
import sys

from pre_commit import color
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.clean import clean
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.install_uninstall import uninstall
from pre_commit.commands.run import run
from pre_commit.error_handler import error_handler
from pre_commit.runner import Runner


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser()

    # http://stackoverflow.com/a/8521644/812183
    parser.add_argument(
        '-V', '--version',
        action='version',
        version='%(prog)s {0}'.format(
            pkg_resources.get_distribution('pre-commit').version
        )
    )

    subparsers = parser.add_subparsers(dest='command')

    install_parser = subparsers.add_parser(
        'install', help='Intall the pre-commit script.',
    )
    install_parser.add_argument(
        '-f', '--overwrite', action='store_true',
        help='Overwrite existing hooks / remove migration mode.',
    )
    install_parser.add_argument(
        '--install-hooks', action='store_true',
        help=(
            'Whether to install hook environments for all environments '
            'in the config file.'
        ),
    )

    subparsers.add_parser('uninstall', help='Uninstall the pre-commit script.')

    subparsers.add_parser('clean', help='Clean out pre-commit files.')

    subparsers.add_parser('autoupdate', help='Auto-update hooks config.')

    run_parser = subparsers.add_parser('run', help='Run hooks.')
    run_parser.add_argument('hook', nargs='?', help='A single hook-id to run')
    run_parser.add_argument(
        '--all-files', '-a', action='store_true', default=False,
        help='Run on all the files in the repo.  Implies --no-stash.',
    )
    run_parser.add_argument(
        '--color', default='auto', type=color.use_color,
        help='Whether to use color in output.  Defaults to `auto`',
    )
    run_parser.add_argument(
        '--no-stash', default=False, action='store_true',
        help='Use this option to prevent auto stashing of unstaged files.',
    )
    run_parser.add_argument(
        '--verbose', '-v', action='store_true', default=False,
    )

    help = subparsers.add_parser(
        'help', help='Show help for a specific command.'
    )
    help.add_argument('help_cmd', nargs='?', help='Command to show help for.')

    # Argparse doesn't really provide a way to use a `default` subparser
    if len(argv) == 0:
        argv = ['run']
    args = parser.parse_args(argv)

    if args.command == 'help':
        if args.help_cmd:
            parser.parse_args([args.help_cmd, '--help'])
        else:
            parser.parse_args(['--help'])

    with error_handler():
        runner = Runner.create()

        if args.command == 'install':
            return install(
                runner, overwrite=args.overwrite, hooks=args.install_hooks,
            )
        elif args.command == 'uninstall':
            return uninstall(runner)
        elif args.command == 'clean':
            return clean(runner)
        elif args.command == 'autoupdate':
            return autoupdate(runner)
        elif args.command == 'run':
            return run(runner, args)
        else:
            raise NotImplementedError(
                'Command {0} not implemented.'.format(args.command)
            )

        raise AssertionError(
            'Command {0} failed to exit with a returncode'.format(args.command)
        )


if __name__ == '__main__':
    exit(main())
