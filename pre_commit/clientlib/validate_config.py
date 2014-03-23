
from __future__ import print_function

import argparse
import re
import sys

import pre_commit.constants as C
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


def validate_config_extra(config):
    for repo in config:
        for hook in repo['hooks']:
            try:
                re.compile(hook['files'])
            except re.error:
                raise InvalidConfigError(
                    'Invalid file regex at {0}, {1}: {2}'.format(
                        repo['repo'], hook['id'], hook['files'],
                    )
                )


validate_config = get_validator(
    C.CONFIG_FILE,
    CONFIG_JSON_SCHEMA,
    InvalidConfigError,
    additional_validation_strategy=validate_config_extra,
)


@entry
def run(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'filename',
        nargs='?', default=None,
        help='Config filename.  Defaults to {0} at root of git repo'.format(
            C.CONFIG_FILE,
        )
    )
    args = parser.parse_args(argv)

    try:
        validate_config(args.filename)
    except InvalidConfigError as e:
        print(e.args[0])
        # If we have more than one exception argument print the stringified
        # version
        if len(e.args) > 1:
            print(str(e.args[1]))
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(run())
