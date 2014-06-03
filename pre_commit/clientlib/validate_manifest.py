import sys

from pre_commit.clientlib.validate_base import get_run_function
from pre_commit.clientlib.validate_base import get_validator
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
            'expected_return_value': {'type': 'number', 'default': 0},
        },
        'required': ['id', 'name', 'entry', 'language'],
    },
}


def additional_manifest_check(obj):
    for hook_config in obj:
        language = hook_config['language']

        if language not in all_languages:
            raise InvalidManifestError(
                'Expected language {0} for {1} to be one of {2!r}'.format(
                    hook_config['id'],
                    hook_config['language'],
                    all_languages,
                )
            )


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
    sys.exit(run())
