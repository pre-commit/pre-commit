
import __builtin__
import pytest
import mock
from plumbum import local

import pre_commit.constants as C
from pre_commit.clientlib.validate_manifest import run, InvalidManifestError, \
    additional_manifest_check


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
        'File {0} is not a valid file'.format(invalid_manifest)
    )


def test_returns_0_for_valid_manifest():
    valid_manifest = 'example_manifest.yaml'
    ret = run(['--filename', valid_manifest])
    assert ret == 0


def test_uses_default_manifest_file_at_root_of_git(empty_git_dir):
    local.path(C.MANIFEST_FILE).write("""
hooks:
    -
        id: foo
        name: Foo
        entry: foo
    """)
    ret = run([])
    assert ret == 0


def test_additional_manifest_check_raises_for_bad_language():
    with pytest.raises(InvalidManifestError):
        additional_manifest_check(
            {'hooks': [{'id': 'foo', 'language': 'not valid'}]}
        )


@pytest.mark.parametrize(('obj'), (
    {'hooks': [{}]},
    {'hooks': [{'language': 'python'}]},
    {'hooks': [{'language': 'python>2.6'}]},
))
def test_additional_manifest_check_is_ok_with_missing_language(obj):
    additional_manifest_check(obj)