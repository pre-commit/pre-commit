from __future__ import unicode_literals

from pre_commit.clientlib.validate_base import get_run_function
from pre_commit.clientlib.validate_base import get_validator
from pre_commit.clientlib.validate_base import is_regex_valid
from pre_commit.languages.all import all_languages


class InvalidManifestError(ValueError):
    pass


MANIFEST_JSON_SCHEMA = {
    'type': 'array',
    'minItems': 1,
    'items': {
        'type': 'object',
        'properties': {
            'id': {'type': 'string'},
            'name': {'type': 'string'},
            'description': {'type': 'string', 'default': ''},
            'entry': {'type': 'string'},
            'language': {'type': 'string'},
            'language_version': {'type': 'string', 'default': 'default'},
            'files': {'type': 'string'},
            'expected_return_value': {'type': 'number', 'default': 0},
        },
        'required': ['id', 'name', 'entry', 'language', 'files'],
    },
}


def validate_languages(hook_config):
    if hook_config['language'] not in all_languages:
        raise InvalidManifestError(
            'Expected language {0} for {1} to be one of {2!r}'.format(
                hook_config['id'],
                hook_config['language'],
                all_languages,
            )
        )


def validate_files(hook_config):
    if not is_regex_valid(hook_config['files']):
        raise InvalidManifestError(
            'Invalid files regex at {0}: {1}'.format(
                hook_config['id'],
                hook_config['files'],
            )
        )


def additional_manifest_check(obj):
    for hook_config in obj:
        validate_languages(hook_config)
        validate_files(hook_config)


load_manifest = get_validator(
    MANIFEST_JSON_SCHEMA,
    InvalidManifestError,
    additional_manifest_check,
)


run = get_run_function(
    'Manifest filenames.',
    load_manifest,
    InvalidManifestError,
)


if __name__ == '__main__':
    exit(run())
