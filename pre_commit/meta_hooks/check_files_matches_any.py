import re
import sys

import pre_commit.constants as C
from pre_commit.clientlib import load_config
from pre_commit.git import get_all_files


def files_matches_any(filenames, include):
    include_re = re.compile(include)
    for filename in filenames:
        if include_re.search(filename):
            return True
    return False


def check_files_matches_any(config_file=None):
    config = load_config(config_file or C.CONFIG_FILE)
    files = get_all_files()
    files_not_matched = False

    for repo in config['repos']:
        for hook in repo['hooks']:
            include = hook.get('files', '')
            if include and not files_matches_any(files, include):
                print(
                    'The files pattern for {} does not match any files'
                    .format(hook['id'])
                )
                files_not_matched = True

    return files_not_matched


if __name__ == '__main__':
    sys.exit(check_files_matches_any())
