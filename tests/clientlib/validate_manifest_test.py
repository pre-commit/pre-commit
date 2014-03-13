
import pytest

from pre_commit.clientlib.validate_manifest import additional_manifest_check
from pre_commit.clientlib.validate_manifest import InvalidManifestError
from pre_commit.clientlib.validate_manifest import run


def test_returns_0_for_valid_manifest():
    assert run(['example_manifest.yaml']) == 0


def test_returns_0_for_our_manifest():
    assert run([]) == 0


def test_returns_1_for_failing():
    assert run(['tests/data/valid_yaml_but_invalid_manifest.yaml']) == 1


def test_additional_manifest_check_raises_for_bad_language():
    with pytest.raises(InvalidManifestError):
        additional_manifest_check([{'id': 'foo', 'language': 'not valid'}])


@pytest.mark.parametrize(('obj'), (
    [{}],
    [{'language': 'python'}],
    [{'language': 'python>2.6'}],
))
def test_additional_manifest_check_is_ok_with_missing_language(obj):
    additional_manifest_check(obj)