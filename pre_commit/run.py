
import argparse


def install():
    """Install the pre-commit hook."""
    raise NotImplementedError


def uninstall():
    """Uninstall the pre-commit hook."""
    raise NotImplementedError


def run_hooks(arguments):
    """Actually run the hooks."""
    raise NotImplementedError


def run(argv):
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        '-i', '--install',
        action='store_true',
        help='Install the pre-commit script.',
    )
    group.add_argument(
        '-u', '--uninstall',
        action='store_true',
        help='Uninstall the pre-commit script.',
    )

    args = parser.parse_args(argv)

    if args.install:
        return install()
    elif args.uninstall:
        return uninstall()
    else:
        return run_hooks(args)