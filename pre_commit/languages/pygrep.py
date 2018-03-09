from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import re
import sys

from pre_commit import output
from pre_commit.languages import helpers
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def _process_filename_by_line(pattern, filename):
    retv = 0
    with open(filename, 'rb') as f:
        for line_no, line in enumerate(f, start=1):
            if pattern.search(line):
                retv = 1
                output.write('{}:{}:'.format(filename, line_no))
                output.write_line(line.rstrip(b'\r\n'))
    return retv


def _process_filename_at_once(pattern, filename):
    retv = 0
    with open(filename, 'rb') as f:
        contents = f.read()
        match = pattern.search(contents)
        if match:
            retv = 1
            line_no = contents[:match.start()].count(b'\n')
            output.write('{}:{}:'.format(filename, line_no + 1))

            matched_lines = match.group().split(b'\n')
            matched_lines[0] = contents.split(b'\n')[line_no]

            output.write_line(b'\n'.join(matched_lines))
    return retv


def run_hook(prefix, hook, file_args):
    exe = (sys.executable, '-m', __name__)
    exe += tuple(hook['args']) + (hook['entry'],)
    return xargs(exe, file_args)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            'grep-like finder using python regexes.  Unlike grep, this tool '
            'returns nonzero when it finds a match and zero otherwise.  The '
            'idea here being that matches are "problems".'
        ),
    )
    parser.add_argument('-i', '--ignore-case', action='store_true')
    parser.add_argument('--multiline', action='store_true')
    parser.add_argument('pattern', help='python regex pattern.')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    flags = re.IGNORECASE if args.ignore_case else 0
    if args.multiline:
        flags |= re.MULTILINE | re.DOTALL

    pattern = re.compile(args.pattern.encode(), flags)

    retv = 0
    for filename in args.filenames:
        if args.multiline:
            retv |= _process_filename_at_once(pattern, filename)
        else:
            retv |= _process_filename_by_line(pattern, filename)
    return retv


if __name__ == '__main__':
    exit(main())
