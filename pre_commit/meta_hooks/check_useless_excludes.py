from __future__ import print_function

import argparse
import re

from cfgv import apply_defaults

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import load_config
from pre_commit.clientlib import MANIFEST_HOOK_DICT


def exclude_matches_any(filenames, include, exclude):
    if exclude == '^$':
        return True
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    for filename in filenames:
        if include_re.search(filename) and exclude_re.search(filename):
            return True
    return False


def check_useless_excludes(config_file):
    config = load_config(config_file)
    files = git.get_all_files()
    retv = 0

    exclude = config['exclude']
    if not exclude_matches_any(files, '', exclude):
        print(
            'The global exclude pattern {!r} does not match any files'
            .format(exclude),
        )
        retv = 1

    for repo in config['repos']:
        for hook in repo['hooks']:
            # Not actually a manifest dict, but this more accurately reflects
            # the defaults applied during runtime
            hook = apply_defaults(hook, MANIFEST_HOOK_DICT)
            include, exclude = hook['files'], hook['exclude']
            if not exclude_matches_any(files, include, exclude):
                print(
                    'The exclude pattern {!r} for {} does not match any files'
                    .format(exclude, hook['id']),
                )
                retv = 1

    return retv


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', default=[C.CONFIG_FILE])
    args = parser.parse_args(argv)

    retv = 0
    for filename in args.filenames:
        retv |= check_useless_excludes(filename)
    return retv


if __name__ == '__main__':
    exit(main())
