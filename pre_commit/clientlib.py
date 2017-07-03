from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import functools

from aspy.yaml import ordered_load
from identify.identify import ALL_TAGS

import pre_commit.constants as C
from pre_commit import schema
from pre_commit.errors import FatalError
from pre_commit.languages.all import all_languages


def check_language(v):
    if v not in all_languages:
        raise schema.ValidationError(
            'Expected {} to be in {!r}'.format(v, all_languages),
        )


def check_type_tag(tag):
    if tag not in ALL_TAGS:
        raise schema.ValidationError(
            'Type tag {!r} is not recognized.  '
            'Try upgrading identify and pre-commit?'.format(tag),
        )


def _make_argparser(filenames_help):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', help=filenames_help)
    parser.add_argument('-V', '--version', action='version', version=C.VERSION)
    return parser


MANIFEST_HOOK_DICT = schema.Map(
    'Hook', 'id',

    schema.Required('id', schema.check_string),
    schema.Required('name', schema.check_string),
    schema.Required('entry', schema.check_string),
    schema.Required(
        'language', schema.check_and(schema.check_string, check_language),
    ),

    schema.Optional(
        'files', schema.check_and(schema.check_string, schema.check_regex),
        '',
    ),
    schema.Optional(
        'exclude',
        schema.check_and(schema.check_string, schema.check_regex),
        '^$',
    ),
    schema.Optional('types', schema.check_array(check_type_tag), ['file']),
    schema.Optional('exclude_types', schema.check_array(check_type_tag), []),

    schema.Optional(
        'additional_dependencies', schema.check_array(schema.check_string), [],
    ),
    schema.Optional('args', schema.check_array(schema.check_string), []),
    schema.Optional('always_run', schema.check_bool, False),
    schema.Optional('pass_filenames', schema.check_bool, True),
    schema.Optional('description', schema.check_string, ''),
    schema.Optional('language_version', schema.check_string, 'default'),
    schema.Optional('log_file', schema.check_string, ''),
    schema.Optional('minimum_pre_commit_version', schema.check_string, '0'),
    schema.Optional('stages', schema.check_array(schema.check_string), []),
)
MANIFEST_SCHEMA = schema.Array(MANIFEST_HOOK_DICT)


class InvalidManifestError(FatalError):
    pass


load_manifest = functools.partial(
    schema.load_from_filename,
    schema=MANIFEST_SCHEMA,
    load_strategy=ordered_load,
    exc_tp=InvalidManifestError,
)


def validate_manifest_main(argv=None):
    parser = _make_argparser('Manifest filenames.')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        try:
            load_manifest(filename)
        except InvalidManifestError as e:
            print(e)
            ret = 1
    return ret


_LOCAL_SENTINEL = 'local'
CONFIG_HOOK_DICT = schema.Map(
    'Hook', 'id',

    schema.Required('id', schema.check_string),

    # All keys in manifest hook dict are valid in a config hook dict, but
    # are optional.
    # No defaults are provided here as the config is merged on top of the
    # manifest.
    *[
        schema.OptionalNoDefault(item.key, item.check_fn)
        for item in MANIFEST_HOOK_DICT.items
        if item.key != 'id'
    ]
)
CONFIG_REPO_DICT = schema.Map(
    'Repository', 'repo',

    schema.Required('repo', schema.check_string),
    schema.RequiredRecurse('hooks', schema.Array(CONFIG_HOOK_DICT)),

    schema.Conditional(
        'sha', schema.check_string,
        condition_key='repo', condition_value=schema.Not(_LOCAL_SENTINEL),
        ensure_absent=True,
    ),
)
CONFIG_SCHEMA = schema.Array(CONFIG_REPO_DICT)


def is_local_repo(repo_entry):
    return repo_entry['repo'] == _LOCAL_SENTINEL


class InvalidConfigError(FatalError):
    pass


load_config = functools.partial(
    schema.load_from_filename,
    schema=CONFIG_SCHEMA,
    load_strategy=ordered_load,
    exc_tp=InvalidConfigError,
)


def validate_config_main(argv=None):
    parser = _make_argparser('Config filenames.')
    args = parser.parse_args(argv)
    ret = 0
    for filename in args.filenames:
        try:
            load_config(filename)
        except InvalidConfigError as e:
            print(e)
            ret = 1
    return ret
