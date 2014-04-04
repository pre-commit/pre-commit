
import re
import sys

from pre_commit.clientlib.validate_base import get_run_function
from pre_commit.clientlib.validate_base import get_validator


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
                        'exclude': {'type': 'string', 'default': '^$'},
                        'args': {
                            'type': 'array',
                            'default': [],
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
            try_regex(repo, hook['id'], hook['exclude'], 'exclude')


load_config = get_validator(
    CONFIG_JSON_SCHEMA,
    InvalidConfigError,
    additional_validation_strategy=validate_config_extra,
)


run = get_run_function('Config filenames.', load_config, InvalidConfigError)


if __name__ == '__main__':
    sys.exit(run())
