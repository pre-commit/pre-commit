import pytest

from pre_commit.clientlib.validate_manifest import additional_manifest_check
from pre_commit.clientlib.validate_manifest import InvalidManifestError
from pre_commit.clientlib.validate_manifest import MANIFEST_JSON_SCHEMA
from pre_commit.clientlib.validate_manifest import run
from testing.util import is_valid_according_to_schema
from testing.util import get_resource_path


@pytest.mark.parametrize(
    ('input', 'expected_output'),
    (
        (['example_hooks.yaml'], 0),
        (['hooks.yaml'], 0),
        (['non_existent_file.yaml'], 1),
        ([get_resource_path('valid_yaml_but_invalid_manifest.yaml')], 1),
        ([get_resource_path('non_parseable_yaml_file.notyaml')], 1),
    ),
)
def test_run(input, expected_output):
    assert run(input) == expected_output


def test_additional_manifest_check_raises_for_bad_language():
    with pytest.raises(InvalidManifestError):
        additional_manifest_check([{'id': 'foo', 'language': 'not valid'}])


@pytest.mark.parametrize(
    'obj',
    (
        [{'language': 'python', 'files': ''}],
        [{'language': 'ruby', 'files': ''}]
    ),
)
def test_additional_manifest_check_passing(obj):
    additional_manifest_check(obj)


@pytest.mark.parametrize(
    'obj',
    (
        [{'id': 'a', 'language': 'not a language', 'files': ''}],
        [{'id': 'a', 'language': 'python3', 'files': ''}],
        [{'id': 'a', 'language': 'python', 'files': 'invalid regex('}],
    ),
)
def test_additional_manifest_failing(obj):
    with pytest.raises(InvalidManifestError):
        additional_manifest_check(obj)


@pytest.mark.parametrize(
    ('manifest_obj', 'expected'),
    (
        ([], False),
        (
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'files': r'\.py$'
            }],
            True,
        ),
        (
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'language_version': 'python3.3',
                'files': r'\.py$',
                'expected_return_value': 0,
            }],
            True,
        ),
    )
)
def test_is_valid_according_to_schema(manifest_obj, expected):
    ret = is_valid_according_to_schema(manifest_obj, MANIFEST_JSON_SCHEMA)
    assert ret is expected
