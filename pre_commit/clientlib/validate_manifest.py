
from __future__ import print_function

import argparse
import sys

import pre_commit.constants as C
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
            'description': {'type': 'string'},
            'entry': {'type': 'string'},
            'language': {'type': 'string'},
            'expected_return_value': {'type': 'number'},
        },
        'required': ['id', 'name', 'entry', 'language'],
    },
}


def additional_manifest_check(obj):
    for hook_config in obj:
        language = hook_config.get('language')

        if language is not None and not any(
            language.startswith(lang) for lang in all_languages
        ):
            raise InvalidManifestError(
                'Expected language {0} for {1} to start with one of {2!r}'.format(
                    hook_config['id'],
                    hook_config['language'],
                    all_languages,
                )
            )


load_manifest = get_validator(
    C.MANIFEST_FILE,
    MANIFEST_JSON_SCHEMA,
    InvalidManifestError,
    additional_manifest_check,
)


@entry
def run(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'filenames',
        nargs='*', default=None,
        help='Manifest filenames.  Defaults to {0} at root of git repo'.format(
            C.MANIFEST_FILE,
        )
    )
    args = parser.parse_args(argv)

    filenames = args.filenames or [C.MANIFEST_FILE]
    retval = 0

    for filename in filenames:
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
