from __future__ import unicode_literals

from pre_commit.clientlib.validate_base import get_run_function
from pre_commit.clientlib.validate_base import get_validator
from pre_commit.clientlib.validate_base import is_regex_valid
from pre_commit.errors import FatalError


_LOCAL_HOOKS_MAGIC_REPO_STRING = 'local'


def is_local_hooks(repo_entry):
    return repo_entry['repo'] == _LOCAL_HOOKS_MAGIC_REPO_STRING


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
                        'always_run': {'type': 'boolean'},
                        'files': {'type': 'string'},
                        'exclude': {'type': 'string'},
                        'language_version': {'type': 'string'},
                        'args': {
                            'type': 'array',
                            'items': {'type': 'string'},
                        },
                        'additional_dependencies': {
                            'type': 'array',
                            'items': {'type': 'string'},
                        },
                    },
                    'required': ['id'],
                }
            }
        },
        'required': ['repo', 'hooks'],
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
        if is_local_hooks(repo):
            if 'sha' in repo:
                raise InvalidConfigError(
                    '"sha" property provided for local hooks'
                )
        elif 'sha' not in repo:
            raise InvalidConfigError(
                'Missing "sha" field for repository {0}'.format(repo['repo'])
            )
        for hook in repo['hooks']:
            try_regex(repo, hook['id'], hook.get('files', ''), 'files')
            try_regex(repo, hook['id'], hook.get('exclude', ''), 'exclude')


load_config = get_validator(
    CONFIG_JSON_SCHEMA,
    InvalidConfigError,
    additional_validation_strategy=validate_config_extra,
)


run = get_run_function('Config filenames.', load_config, InvalidConfigError)


if __name__ == '__main__':
    exit(run())
