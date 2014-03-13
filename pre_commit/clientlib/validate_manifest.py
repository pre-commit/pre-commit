
from __future__ import print_function

import argparse

import pre_commit.constants as C
from pre_commit.clientlib.validate_base import get_validator


class InvalidManifestError(ValueError): pass


MANIFEST_JSON_SCHEMA = {
    'type': 'object',
    'properties': {
        'hooks': {
            'type': 'array',
            'minItems': 1,
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'name': {'type': 'string'},
                    'description': {'type': 'string'},
                    'entry': {'type': 'string'},
                    'language': {'type': 'string'},
                    'expected_return_value': {'type': 'number'},
                },
                'required': ['id', 'name', 'entry'],
            },
        },
    },
    'required': ['hooks'],
}


def additional_manifest_check(obj):
    for hook_config in obj['hooks']:
        language = hook_config.get('language')

        if language is not None and not any(
            language.startswith(lang) for lang in C.SUPPORTED_LANGUAGES
        ):
            raise InvalidManifestError(
                'Expected language {0} for {1} to start with one of {2!r}'.format(
                    hook_config['id'],
                    hook_config['language'],
                    C.SUPPORTED_LANGUAGES,
                )
            )


validate_manifest = get_validator(
    C.MANIFEST_FILE,
    MANIFEST_JSON_SCHEMA,
    InvalidManifestError,
    additional_manifest_check,
)


def run(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--filename',
        required=False, default=None,
        help='Manifest filename.  Defaults to {0} at root of git repo'.format(
            C.MANIFEST_FILE,
        )
    )
    args = parser.parse_args(argv)

    try:
        validate_manifest(args.filename)
    except InvalidManifestError as e:
        print(e.args[0])
        # If we have more than one exception argument print the stringified
        # version
        if len(e.args) > 1:
            print(str(e.args[1]))
        return 1

    return 0