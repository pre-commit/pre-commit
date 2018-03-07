from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import collections
import functools

import cfgv
from aspy.yaml import ordered_load
from identify.identify import ALL_TAGS

import pre_commit.constants as C
from pre_commit.error_handler import FatalError
from pre_commit.languages.all import all_languages


def check_type_tag(tag):
    if tag not in ALL_TAGS:
        raise cfgv.ValidationError(
            'Type tag {!r} is not recognized.  '
            'Try upgrading identify and pre-commit?'.format(tag),
        )


def _make_argparser(filenames_help):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', help=filenames_help)
    parser.add_argument('-V', '--version', action='version', version=C.VERSION)
    return parser


MANIFEST_HOOK_DICT = cfgv.Map(
    'Hook', 'id',

    cfgv.Required('id', cfgv.check_string),
    cfgv.Required('name', cfgv.check_string),
    cfgv.Required('entry', cfgv.check_string),
    cfgv.Required('language', cfgv.check_one_of(all_languages)),

    cfgv.Optional(
        'files', cfgv.check_and(cfgv.check_string, cfgv.check_regex), '',
    ),
    cfgv.Optional(
        'exclude', cfgv.check_and(cfgv.check_string, cfgv.check_regex), '^$',
    ),
    cfgv.Optional('types', cfgv.check_array(check_type_tag), ['file']),
    cfgv.Optional('exclude_types', cfgv.check_array(check_type_tag), []),

    cfgv.Optional(
        'additional_dependencies', cfgv.check_array(cfgv.check_string), [],
    ),
    cfgv.Optional('args', cfgv.check_array(cfgv.check_string), []),
    cfgv.Optional('always_run', cfgv.check_bool, False),
    cfgv.Optional('pass_filenames', cfgv.check_bool, True),
    cfgv.Optional('description', cfgv.check_string, ''),
    cfgv.Optional('language_version', cfgv.check_string, 'default'),
    cfgv.Optional('log_file', cfgv.check_string, ''),
    cfgv.Optional('minimum_pre_commit_version', cfgv.check_string, '0'),
    cfgv.Optional('stages', cfgv.check_array(cfgv.check_one_of(C.STAGES)), []),
    cfgv.Optional('verbose', cfgv.check_bool, False),
)
MANIFEST_SCHEMA = cfgv.Array(MANIFEST_HOOK_DICT)


class InvalidManifestError(FatalError):
    pass


load_manifest = functools.partial(
    cfgv.load_from_filename,
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
_META_SENTINEL = 'meta'


class MigrateShaToRev(object):
    @staticmethod
    def _cond(key):
        return cfgv.Conditional(
            key, cfgv.check_string,
            condition_key='repo',
            condition_value=cfgv.NotIn(_LOCAL_SENTINEL, _META_SENTINEL),
            ensure_absent=True,
        )

    def check(self, dct):
        if dct.get('repo') in {_LOCAL_SENTINEL, _META_SENTINEL}:
            self._cond('rev').check(dct)
            self._cond('sha').check(dct)
        elif 'sha' in dct and 'rev' in dct:
            raise cfgv.ValidationError('Cannot specify both sha and rev')
        elif 'sha' in dct:
            self._cond('sha').check(dct)
        else:
            self._cond('rev').check(dct)

    def apply_default(self, dct):
        if 'sha' in dct:
            dct['rev'] = dct.pop('sha')

    def remove_default(self, dct):
        pass


CONFIG_HOOK_DICT = cfgv.Map(
    'Hook', 'id',

    cfgv.Required('id', cfgv.check_string),

    # All keys in manifest hook dict are valid in a config hook dict, but
    # are optional.
    # No defaults are provided here as the config is merged on top of the
    # manifest.
    *[
        cfgv.OptionalNoDefault(item.key, item.check_fn)
        for item in MANIFEST_HOOK_DICT.items
        if item.key != 'id'
    ]
)
CONFIG_REPO_DICT = cfgv.Map(
    'Repository', 'repo',

    cfgv.Required('repo', cfgv.check_string),
    cfgv.RequiredRecurse('hooks', cfgv.Array(CONFIG_HOOK_DICT)),

    MigrateShaToRev(),
)
CONFIG_SCHEMA = cfgv.Map(
    'Config', None,

    cfgv.RequiredRecurse('repos', cfgv.Array(CONFIG_REPO_DICT)),
    cfgv.Optional('exclude', cfgv.check_regex, '^$'),
    cfgv.Optional('fail_fast', cfgv.check_bool, False),
)


def is_local_repo(repo_entry):
    return repo_entry['repo'] == _LOCAL_SENTINEL


def is_meta_repo(repo_entry):
    return repo_entry['repo'] == _META_SENTINEL


class InvalidConfigError(FatalError):
    pass


def ordered_load_normalize_legacy_config(contents):
    data = ordered_load(contents)
    if isinstance(data, list):
        # TODO: Once happy, issue a deprecation warning and instructions
        return collections.OrderedDict([('repos', data)])
    else:
        return data


load_config = functools.partial(
    cfgv.load_from_filename,
    schema=CONFIG_SCHEMA,
    load_strategy=ordered_load_normalize_legacy_config,
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
