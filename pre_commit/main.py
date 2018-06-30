from __future__ import unicode_literals

import argparse
import logging
import os
import sys

import pre_commit.constants as C
from pre_commit import color
from pre_commit import five
from pre_commit import git
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.clean import clean
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.install_uninstall import install_hooks
from pre_commit.commands.install_uninstall import uninstall
from pre_commit.commands.migrate_config import migrate_config
from pre_commit.commands.run import run
from pre_commit.commands.sample_config import sample_config
from pre_commit.commands.try_repo import try_repo
from pre_commit.error_handler import error_handler
from pre_commit.logging_handler import add_logging_handler
from pre_commit.runner import Runner
from pre_commit.store import Store


logger = logging.getLogger('pre_commit')

# https://github.com/pre-commit/pre-commit/issues/217
# On OSX, making a virtualenv using pyvenv at . causes `virtualenv` and `pip`
# to install packages to the wrong place.  We don't want anything to deal with
# pyvenv
os.environ.pop('__PYVENV_LAUNCHER__', None)


def _add_color_option(parser):
    parser.add_argument(
        '--color', default='auto', type=color.use_color,
        metavar='{' + ','.join(color.COLOR_CHOICES) + '}',
        help='Whether to use color in output.  Defaults to `%(default)s`.',
    )


def _add_config_option(parser):
    parser.add_argument(
        '-c', '--config', default=C.CONFIG_FILE,
        help='Path to alternate config file',
    )


def _add_hook_type_option(parser):
    parser.add_argument(
        '-t', '--hook-type', choices=('pre-commit', 'pre-push', 'commit-msg'),
        default='pre-commit',
    )


def _add_run_options(parser):
    parser.add_argument('hook', nargs='?', help='A single hook-id to run')
    parser.add_argument('--verbose', '-v', action='store_true', default=False)
    parser.add_argument(
        '--origin', '-o',
        help="The origin branch's commit_id when using `git push`.",
    )
    parser.add_argument(
        '--source', '-s',
        help="The remote branch's commit_id when using `git push`.",
    )
    parser.add_argument(
        '--commit-msg-filename',
        help='Filename to check when running during `commit-msg`',
    )
    parser.add_argument(
        '--hook-stage', choices=C.STAGES, default='commit',
        help='The stage during which the hook is fired.  One of %(choices)s',
    )
    parser.add_argument(
        '--show-diff-on-failure', action='store_true',
        help='When hooks fail, run `git diff` directly afterward.',
    )
    mutex_group = parser.add_mutually_exclusive_group(required=False)
    mutex_group.add_argument(
        '--all-files', '-a', action='store_true', default=False,
        help='Run on all the files in the repo.',
    )
    mutex_group.add_argument(
        '--files', nargs='*', default=[],
        help='Specific filenames to run hooks on.',
    )


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    argv = [five.to_text(arg) for arg in argv]
    parser = argparse.ArgumentParser()

    # https://stackoverflow.com/a/8521644/812183
    parser.add_argument(
        '-V', '--version',
        action='version',
        version='%(prog)s {}'.format(C.VERSION),
    )

    subparsers = parser.add_subparsers(dest='command')

    install_parser = subparsers.add_parser(
        'install', help='Install the pre-commit script.',
    )
    _add_color_option(install_parser)
    _add_config_option(install_parser)
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
    _add_hook_type_option(install_parser)
    install_parser.add_argument(
        '--allow-missing-config', action='store_true', default=False,
        help=(
            'Whether to allow a missing `pre-commit` configuration file '
            'or exit with a failure code.'
        ),
    )

    install_hooks_parser = subparsers.add_parser(
        'install-hooks',
        help=(
            'Install hook environments for all environments in the config '
            'file.  You may find `pre-commit install --install-hooks` more '
            'useful.'
        ),
    )
    _add_color_option(install_hooks_parser)
    _add_config_option(install_hooks_parser)

    uninstall_parser = subparsers.add_parser(
        'uninstall', help='Uninstall the pre-commit script.',
    )
    _add_color_option(uninstall_parser)
    _add_config_option(uninstall_parser)
    _add_hook_type_option(uninstall_parser)

    clean_parser = subparsers.add_parser(
        'clean', help='Clean out pre-commit files.',
    )
    _add_color_option(clean_parser)
    _add_config_option(clean_parser)
    autoupdate_parser = subparsers.add_parser(
        'autoupdate',
        help="Auto-update pre-commit config to the latest repos' versions.",
    )
    _add_color_option(autoupdate_parser)
    _add_config_option(autoupdate_parser)
    autoupdate_parser.add_argument(
        '--tags-only', action='store_true', help='LEGACY: for compatibility',
    )
    autoupdate_parser.add_argument(
        '--bleeding-edge', action='store_true',
        help=(
            'Update to the bleeding edge of `master` instead of the latest '
            'tagged version (the default behavior).'
        ),
    )
    autoupdate_parser.add_argument(
        '--repo', dest='repos', action='append', metavar='REPO',
        help='Only update this repository -- may be specified multiple times.',
    )

    migrate_config_parser = subparsers.add_parser(
        'migrate-config',
        help='Migrate list configuration to new map configuration.',
    )
    _add_color_option(migrate_config_parser)
    _add_config_option(migrate_config_parser)

    run_parser = subparsers.add_parser('run', help='Run hooks.')
    _add_color_option(run_parser)
    _add_config_option(run_parser)
    _add_run_options(run_parser)

    sample_config_parser = subparsers.add_parser(
        'sample-config', help='Produce a sample {} file'.format(C.CONFIG_FILE),
    )
    _add_color_option(sample_config_parser)
    _add_config_option(sample_config_parser)

    try_repo_parser = subparsers.add_parser(
        'try-repo',
        help='Try the hooks in a repository, useful for developing new hooks.',
    )
    _add_color_option(try_repo_parser)
    _add_config_option(try_repo_parser)
    try_repo_parser.add_argument(
        'repo', help='Repository to source hooks from.',
    )
    try_repo_parser.add_argument(
        '--ref', '--rev',
        help=(
            'Manually select a rev to run against, otherwise the `HEAD` '
            'revision will be used.'
        ),
    )
    _add_run_options(try_repo_parser)

    help = subparsers.add_parser(
        'help', help='Show help for a specific command.',
    )
    help.add_argument('help_cmd', nargs='?', help='Command to show help for.')

    # argparse doesn't really provide a way to use a `default` subparser
    if len(argv) == 0:
        argv = ['run']
    args = parser.parse_args(argv)

    if args.command == 'help' and args.help_cmd:
        parser.parse_args([args.help_cmd, '--help'])
    elif args.command == 'help':
        parser.parse_args(['--help'])
    elif args.command in {'run', 'try-repo'}:
        args.files = [
            os.path.relpath(os.path.abspath(filename), git.get_root())
            for filename in args.files
        ]

    with error_handler():
        add_logging_handler(args.color)
        runner = Runner.create(args.config)
        store = Store()
        git.check_for_cygwin_mismatch()

        if args.command == 'install':
            return install(
                runner, store,
                overwrite=args.overwrite, hooks=args.install_hooks,
                hook_type=args.hook_type,
                skip_on_missing_conf=args.allow_missing_config,
            )
        elif args.command == 'install-hooks':
            return install_hooks(runner, store)
        elif args.command == 'uninstall':
            return uninstall(runner, hook_type=args.hook_type)
        elif args.command == 'clean':
            return clean(store)
        elif args.command == 'autoupdate':
            if args.tags_only:
                logger.warning('--tags-only is the default')
            return autoupdate(
                runner, store,
                tags_only=not args.bleeding_edge,
                repos=args.repos,
            )
        elif args.command == 'migrate-config':
            return migrate_config(runner)
        elif args.command == 'run':
            return run(runner, store, args)
        elif args.command == 'sample-config':
            return sample_config()
        elif args.command == 'try-repo':
            return try_repo(args)
        else:
            raise NotImplementedError(
                'Command {} not implemented.'.format(args.command),
            )

        raise AssertionError(
            'Command {} failed to exit with a returncode'.format(args.command),
        )


if __name__ == '__main__':
    exit(main())
