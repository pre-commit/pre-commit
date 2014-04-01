
from __future__ import print_function

import argparse
import re
import sys

from pre_commit.clientlib.validate_base import get_validator
from pre_commit.util import entry


class InvalidConfigError(ValueError): pass


CONFIG_JSON_SCHEMA = {
    'type': 'array',
    'minItems': 1,
    'items': {
        'type': 'object',
        'properties': {
            'repo': {'type': 'string'},
            'sha': {'type': 'string'},
            'hooks': {
                'type': 'array',
                'minItems': 1,
                'items': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'string'},
                        'files': {'type': 'string'},
                        'exclude': {'type': 'string'},
                        'args': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {'type': 'string'},
                        },
                    },
                    'required': ['id', 'files'],
                }
            }
        },
        'required': ['repo', 'sha', 'hooks'],
    }
}


def try_regex(repo, hook, value, field_name):
    try:
        re.compile(value)
    except re.error:
        raise InvalidConfigError(
            'Invalid {0} regex at {1}, {2}: {3}'.format(
                field_name, repo, hook, value,
            )
        )


def validate_config_extra(config):
    for repo in config:
        for hook in repo['hooks']:
            try_regex(repo, hook['id'], hook['files'], 'files')
            try_regex(repo, hook['id'], hook.get('exclude', ''), 'exclude')


load_config = get_validator(
    CONFIG_JSON_SCHEMA,
    InvalidConfigError,
    additional_validation_strategy=validate_config_extra,
)


@entry
def run(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', help='Config filenames.')
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            load_config(filename)
        except InvalidConfigError as e:
            print(e.args[0])
            # If we have more than one exception argument print the stringified
            # version
            if len(e.args) > 1:
                print(str(e.args[1]))
            retval = 1
    return retval


if __name__ == '__main__':
    sys.exit(run())
