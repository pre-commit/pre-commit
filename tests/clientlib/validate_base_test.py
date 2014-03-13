
import __builtin__

import os.path
import mock
import pytest

from pre_commit import git
from pre_commit.clientlib.validate_base import get_validator


class AdditionalValidatorError(ValueError): pass


@pytest.fixture
def noop_validator():
    return get_validator('example_manifest.yaml', {}, ValueError)


@pytest.fixture
def array_validator():
    return get_validator('', {'type': 'array'}, ValueError)


@pytest.fixture
def additional_validator():
    def raises_always(obj):
        raise AdditionalValidatorError

    return get_validator(
        'example_manifest.yaml',
        {},
        ValueError,
        additional_validation_strategy=raises_always,
    )


def test_raises_for_non_existent_file(noop_validator):
    with pytest.raises(ValueError):
        noop_validator('file_that_does_not_exist.yaml')


def test_raises_for_invalid_yaml_file(noop_validator):
    with pytest.raises(ValueError):
        noop_validator('tests/data/non_parseable_yaml_file.yaml')


def test_defaults_to_backup_filename(noop_validator):
    with mock.patch.object(__builtin__, 'open', side_effect=open) as mock_open:
        noop_validator()
        mock_open.assert_called_once_with(
            os.path.join(git.get_root(), 'example_manifest.yaml'), 'r',
        )


def test_raises_for_failing_schema(array_validator):
    with pytest.raises(ValueError):
        array_validator('tests/data/non_parseable_yaml_file.yaml')


def test_raises_when_additional_validation_fails(additional_validator):
    with pytest.raises(AdditionalValidatorError):
        additional_validator()