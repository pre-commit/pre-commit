
import __builtin__
import jsonschema
import pytest
import mock

from pre_commit.clientlib.validate_manifest import check_is_valid_manifest
from pre_commit.clientlib.validate_manifest import InvalidManifestError
from pre_commit.clientlib.validate_manifest import run


@pytest.yield_fixture
def print_mock():
    with mock.patch.object(__builtin__, 'print', autospec=True) as print_mock_obj:
        yield print_mock_obj


def test_run_returns_1_for_non_existent_module(print_mock):
    non_existent_filename = 'file_that_does_not_exist'
    ret = run(['--filename', non_existent_filename])
    assert ret == 1
    print_mock.assert_called_once_with(
        'File {0} does not exist'.format(non_existent_filename),
    )


def test_run_returns_1_for_non_yaml_file(print_mock):
    non_parseable_filename = 'tests/data/non_parseable_yaml_file.yaml'
    ret = run(['--filename', non_parseable_filename])
    assert ret == 1
    print_mock.assert_any_call(
        'File {0} is not a valid yaml file'.format(non_parseable_filename),
    )


def test_returns_1_for_valid_yaml_file_but_invalid_manifest(print_mock):
    invalid_manifest = 'tests/data/valid_yaml_but_invalid_manifest.yaml'
    ret = run(['--filename', invalid_manifest])
    assert ret == 1
    print_mock.assert_any_call(
        'File {0} is not a valid manifest file'.format(invalid_manifest)
    )


def test_returns_0_for_valid_manifest():
    valid_manifest = 'example_manifest.yaml'
    ret = run(['--filename', valid_manifest])
    assert ret == 0


@pytest.mark.parametrize(('manifest', 'expected_exception_type'), (
    (
        """
hooks:
    -
        id: foo
        entry: foo
        """,
        jsonschema.exceptions.ValidationError,
    ),
    (
        """
hooks:
    -
        id: foo
        name: Foo
        language: Not a Language lol
        entry: foo
        """,
        InvalidManifestError,
    ),
))
def test_check_invalid_manifests(manifest, expected_exception_type):
    with pytest.raises(expected_exception_type):
        check_is_valid_manifest(manifest)


def test_valid_manifest_is_valid():
    check_is_valid_manifest("""
hooks:
    -
        id: foo
        name: Foo
        entry: foo
        language: python>2.6
    """)
