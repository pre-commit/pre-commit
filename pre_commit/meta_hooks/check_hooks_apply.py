import argparse

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import load_config
from pre_commit.commands.run import _filter_by_include_exclude
from pre_commit.commands.run import _filter_by_types
from pre_commit.repository import repositories
from pre_commit.store import Store


def check_all_hooks_match_files(config_file):
    files = git.get_all_files()
    retv = 0

    for repo in repositories(load_config(config_file), Store()):
        for hook_id, hook in repo.hooks:
            if hook['always_run']:
                continue
            include, exclude = hook['files'], hook['exclude']
            filtered = _filter_by_include_exclude(files, include, exclude)
            types, exclude_types = hook['types'], hook['exclude_types']
            filtered = _filter_by_types(filtered, types, exclude_types)
            if not filtered:
                print('{} does not apply to this repository'.format(hook_id))
                retv = 1

    return retv


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', default=[C.CONFIG_FILE])
    args = parser.parse_args(argv)

    retv = 0
    for filename in args.filenames:
        retv |= check_all_hooks_match_files(filename)
    return retv


if __name__ == '__main__':
    exit(main())
