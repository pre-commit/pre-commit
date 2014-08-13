from __future__ import unicode_literals

from pre_commit.clientlib.validate_base import get_run_function
from pre_commit.clientlib.validate_base import get_validator
from pre_commit.clientlib.validate_base import is_regex_valid
from pre_commit.errors import FatalError


class InvalidConfigError(FatalError):
    pass


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
                        'language_version': {'type': 'string'},
                        'args': {
                            'type': 'array',
                            'default': [],
                            'items': {'type': 'string'},
                        },
                    },
                    'required': ['id'],
                }
            }
        },
        'required': ['repo', 'sha', 'hooks'],
    }
}


def try_regex(repo, hook, value, field_name):
    if not is_regex_valid(value):
        raise InvalidConfigError(
            'Invalid {0} regex at {1}, {2}: {3}'.format(
                field_name, repo, hook, value,
            )
        )


def validate_config_extra(config):
    for repo in config:
        for hook in repo['hooks']:
            try_regex(repo, hook['id'], hook.get('files', ''), 'files')
            try_regex(repo, hook['id'], hook['exclude'], 'exclude')


load_config = get_validator(
    CONFIG_JSON_SCHEMA,
    InvalidConfigError,
    additional_validation_strategy=validate_config_extra,
)


run = get_run_function('Config filenames.', load_config, InvalidConfigError)


if __name__ == '__main__':
    exit(run())
