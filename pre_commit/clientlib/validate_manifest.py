
from __future__ import print_function

import argparse
import jsonschema
import jsonschema.exceptions
import os.path
import yaml

import pre_commit.constants as C
from pre_commit import git


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


def check_is_valid_manifest(file_contents):
    file_objects = yaml.load(file_contents)

    jsonschema.validate(file_objects, MANIFEST_JSON_SCHEMA)

    for hook_config in file_objects['hooks']:
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

    if args.filename is None:
        filename = os.path.join(git.get_root(), C.MANIFEST_FILE)
    else:
        filename = args.filename

    if not os.path.exists(filename):
        print('File {0} does not exist'.format(filename))
        return 1

    file_contents = open(filename, 'r').read()

    try:
        yaml.load(file_contents)
    except Exception as e:
        print('File {0} is not a valid yaml file'.format(filename))
        print(str(e))
        return 1

    try:
        check_is_valid_manifest(file_contents)
    except (jsonschema.exceptions.ValidationError, InvalidManifestError) as e:
        print('File {0} is not a valid manifest file'.format(filename))
        print(str(e))
        return 1

    return 0