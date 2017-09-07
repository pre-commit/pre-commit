from __future__ import print_function
from __future__ import unicode_literals

import io

import yaml
from aspy.yaml import ordered_load


def _indent(s):
    lines = s.splitlines(True)
    return ''.join(' ' * 4 + line if line.strip() else line for line in lines)


def _is_header_line(line):
    return (line.startswith(('#', '---')) or not line.strip())


def migrate_config(runner, quiet=False):
    with io.open(runner.config_file_path) as f:
        contents = f.read()

    # Find the first non-header line
    lines = contents.splitlines(True)
    i = 0
    while _is_header_line(lines[i]):
        i += 1

    header = ''.join(lines[:i])
    rest = ''.join(lines[i:])

    if isinstance(ordered_load(contents), list):
        # If they are using the "default" flow style of yaml, this operation
        # will yield a valid configuration
        try:
            trial_contents = header + 'repos:\n' + rest
            yaml.load(trial_contents)
            contents = trial_contents
        except yaml.YAMLError:
            contents = header + 'repos:\n' + _indent(rest)

        with io.open(runner.config_file_path, 'w') as f:
            f.write(contents)

        print('Configuration has been migrated.')
    elif not quiet:
        print('Configuration is already migrated.')
