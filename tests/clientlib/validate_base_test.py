import pytest

from pre_commit.clientlib.validate_base import get_validator
from pre_commit.ordereddict import OrderedDict
from pre_commit.yaml_extensions import ordered_load
from testing.util import get_resource_path


class AdditionalValidatorError(ValueError):
    pass


@pytest.fixture
def noop_validator():
    return get_validator({}, ValueError)


@pytest.fixture
def array_validator():
    return get_validator({'type': 'array'}, ValueError)


@pytest.fixture
def additional_validator():
    def raises_always(_):
        raise AdditionalValidatorError

    return get_validator(
        {},
        ValueError,
        additional_validation_strategy=raises_always,
    )


def test_raises_for_non_existent_file(noop_validator):
    with pytest.raises(ValueError):
        noop_validator('file_that_does_not_exist.yaml')


def test_raises_for_invalid_yaml_file(noop_validator):
    with pytest.raises(ValueError):
        noop_validator(get_resource_path('non_parseable_yaml_file.notyaml'))


def test_raises_for_failing_schema(array_validator):
    with pytest.raises(ValueError):
        array_validator(get_resource_path('valid_yaml_but_invalid_manifest.yaml'))


def test_passes_array_schema(array_validator):
    array_validator(get_resource_path('array_yaml_file.yaml'))


def test_raises_when_additional_validation_fails(additional_validator):
    with pytest.raises(AdditionalValidatorError):
        additional_validator(get_resource_path('array_yaml_file.yaml'))


def test_returns_object_after_validating(noop_validator):
    ret = noop_validator(get_resource_path('array_yaml_file.yaml'))
    assert ret == ['foo', 'bar']


def test_load_strategy(noop_validator):
    ret = noop_validator(
        get_resource_path('ordering_data_test.yaml'),
        load_strategy=ordered_load,
    )
    assert type(ret) is OrderedDict
