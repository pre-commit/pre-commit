import re
import sys

import pre_commit.constants as C
from pre_commit.clientlib import load_config
from pre_commit.git import get_all_files


def exclude_matches_any(filenames, include, exclude):
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    for filename in filenames:
        if include_re.search(filename) and exclude_re.search(filename):
            return True
    return False


def check_useless_excludes(config_file=None):
    config = load_config(config_file or C.CONFIG_FILE)
    files = get_all_files()
    useless_excludes = False

    exclude = config.get('exclude')
    if exclude != '^$' and not exclude_matches_any(files, '', exclude):
        print('The global exclude pattern does not match any files')
        useless_excludes = True

    for repo in config['repos']:
        for hook in repo['hooks']:
            include, exclude = hook.get('files', ''), hook.get('exclude')
            if exclude and not exclude_matches_any(files, include, exclude):
                print(
                    'The exclude pattern for {} does not match any files'
                    .format(hook['id'])
                )
                useless_excludes = True

    return useless_excludes


if __name__ == '__main__':
    sys.exit(check_useless_excludes())
