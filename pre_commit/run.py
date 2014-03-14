
import argparse
import os.path
import subprocess

from pre_commit import git
from pre_commit.clientlib.validate_config import validate_config
from pre_commit.repository import Repository


RED = '\033[41m'
GREEN = '\033[42m'
NORMAL = '\033[0m'
COLS = int(subprocess.Popen(['tput', 'cols'], stdout=subprocess.PIPE).communicate()[0])


def install():
    """Install the pre-commit hook."""
    git.create_pre_commit()


def uninstall():
    """Uninstall the pre-commit hook."""
    git.remove_pre_commit()


def _run_single_hook(repository, hook_id, run_all_the_things=False):
    repository.install()

    if run_all_the_things:
        get_filenames = git.get_all_files_matching
    else:
        get_filenames = git.get_staged_files_matching

    hook = repository.hooks[hook_id]

    retcode, stdout, stderr = repository.run_hook(
        hook_id,
        map(os.path.abspath, get_filenames(hook['files'])),
    )

    if retcode != repository.hooks[hook_id].get('expected_return_value', 0):
        output = '\n'.join([stdout, stderr]).strip()
        retcode = 1
        color = RED
        pass_fail = 'Failed'
    else:
        output = ''
        retcode = 0
        color = GREEN
        pass_fail = 'Passed'


    print '{0}{1}{2}{3}{4}'.format(
        hook['name'],
        '.' * (COLS - len(hook['name']) - len(pass_fail) - 6),
        color,
        pass_fail,
        NORMAL,
    )

    if output:
        print
        print output
        print

    return retcode


def run_hooks(run_all_the_things=False):
    """Actually run the hooks."""
    retval = 0

    configs = validate_config([])
    for config in configs:
        repo = Repository(config)
        for hook_id in repo.hooks:
            retval |= _run_single_hook(
                repo,
                hook_id,
                run_all_the_things=run_all_the_things,
            )

    return retval


def run_single_hook(hook_id, configs=None, run_all_the_things=False):
    configs = configs or validate_config([])
    for config in configs:
        repo = Repository(config)
        if hook_id in repo.hooks:
            return _run_single_hook(
                repo,
                hook_id,
                run_all_the_things=run_all_the_things,
            )
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

    parser.add_argument(
        '--run-fucking-everything', action='store_true', default=False,
        help='Run on all the files in the repo',
    )

    args = parser.parse_args(argv)

    if args.install:
        return install()
    elif args.uninstall:
        return uninstall()
    elif args.run:
        return run_single_hook(args.run, run_all_the_things=args.run_fucking_everything)
    else:
        return run_hooks(run_all_the_things=args.run_fucking_everything)
