
from __future__ import print_function

import argparse
import sys

from pre_commit.clientlib.validate_base import get_validator
from pre_commit.languages.all import all_languages
from pre_commit.util import entry


class InvalidManifestError(ValueError): pass


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
            'expected_return_value': {'type': 'number', 'default': 0},
        },
        'required': ['id', 'name', 'entry', 'language'],
    },
}


def additional_manifest_check(obj):
    for hook_config in obj:
        language = hook_config['language']

        if not any(language.startswith(lang) for lang in all_languages):
            raise InvalidManifestError(
                'Expected language {0} for {1} to start with one of {2!r}'.format(
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


@entry
def run(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', help='Manifest filenames.')
    args = parser.parse_args(argv)

    retval = 0
    for filename in args.filenames:
        try:
            load_manifest(filename)
        except InvalidManifestError as e:
            print(e.args[0])
            # If we have more than one exception argument print the stringified
            # version
            if len(e.args) > 1:
                print(str(e.args[1]))
            retval = 1
    return retval


if __name__ == '__main__':
    sys.exit(run())
