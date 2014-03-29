
import mock
import pytest
import subprocess

from pre_commit.prefixed_command_runner import _replace_cmd
from pre_commit.prefixed_command_runner import PrefixedCommandRunner


@pytest.fixture
def popen_mock():
    popen = mock.Mock()
    popen.return_value.communicate.return_value = (mock.Mock(), mock.Mock())
    return popen


@pytest.mark.parametrize(('input', 'kwargs', 'expected_output'), (
    ([], {}, []),
    (['foo'], {}, ['foo']),
    ([], {'foo': 'bar'}, []),
    (['{foo}/baz'], {'foo': 'bar'}, ['bar/baz']),
    (['foo'], {'foo': 'bar'}, ['foo']),
    (['foo', '{bar}'], {'bar': 'baz'}, ['foo', 'baz']),
))
def test_replace_cmd(input, kwargs, expected_output):
    ret = _replace_cmd(input, **kwargs)
    assert ret == expected_output


@pytest.mark.parametrize(('input', 'expected_prefix'), (
    ('.', './'),
    ('foo', 'foo/'),
    ('bar/', 'bar/'),
    ('foo/bar', 'foo/bar/'),
    ('foo/bar/', 'foo/bar/'),
))
def test_init_normalizes_path_endings(input, expected_prefix):
    instance = PrefixedCommandRunner(input)
    assert instance.prefix_dir == expected_prefix


def test_run_substitutes_prefix(popen_mock):
    instance = PrefixedCommandRunner('prefix', popen=popen_mock)
    ret = instance.run(['{prefix}bar', 'baz'])
    popen_mock.assert_called_once_with(
        ['prefix/bar', 'baz'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert ret == (
        popen_mock.return_value.returncode,
        popen_mock.return_value.communicate.return_value[0],
        popen_mock.return_value.communicate.return_value[1],
    )


@pytest.mark.parametrize(('first_prefix', 'postfix', 'expected_output'), (
    ('foo', '', 'foo/'),
    ('foo', 'bar', 'foo/bar/'),
    ('./', 'bar', './bar/'),
))
def test_from_command_runner(first_prefix, postfix, expected_output):
    first = PrefixedCommandRunner(first_prefix)
    second = PrefixedCommandRunner.from_command_runner(first, postfix)
    assert second.prefix_dir == expected_output


def test_from_command_runner_preserves_popen(popen_mock):
    first = PrefixedCommandRunner('foo', popen=popen_mock)
    second = PrefixedCommandRunner.from_command_runner(first, 'bar')
    second.run(['foo/bar/baz'])
    popen_mock.assert_called_once_with(
        ['foo/bar/baz'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
