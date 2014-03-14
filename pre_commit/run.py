
import argparse
import os.path
from pre_commit import git
from pre_commit.clientlib.validate_config import validate_config
from pre_commit.repository import Repository

def install():
    """Install the pre-commit hook."""
    git.create_pre_commit()


def uninstall():
    """Uninstall the pre-commit hook."""
    git.remove_pre_commit()


def run_hooks(arguments):
    """Actually run the hooks."""
    raise NotImplementedError

def run_single_hook(hook_id):
    configs = validate_config([])
    for config in configs:
        repo = Repository(config)
        if hook_id in repo.hooks:
            repo.install()

            retcode, stdout, stderr = repo.run_hook(hook_id, map(os.path.abspath, ['pre_commit/constants.py']))

            if retcode != repo.hooks[hook_id].get('expected_return_value', 0):
                for out in (stdout, stderr):
                    out = out.rstrip()
                    if len(out) > 0:
                        print out
                return 1
            else:
                return 0
    else:
        print "No hook with id {0}".format(hook_id)
        return 1


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
    group.add_argument(
        '-r', '--run',
        help='Run a hook'
    )

    args = parser.parse_args(argv)

    if args.install:
        return install()
    elif args.uninstall:
        return uninstall()
    elif args.run:
        return run_single_hook(args.run)
    else:
        return run_hooks(args)
