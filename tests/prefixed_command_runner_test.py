from __future__ import unicode_literals

import os
import mock
import pytest
import subprocess

from pre_commit.prefixed_command_runner import _replace_cmd
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.util import CalledProcessError


def test_CalledProcessError_str():
    error = CalledProcessError(
        1, [str('git'), str('status')], 0, (str('stdout'), str('stderr'))
    )
    assert str(error) == (
        "Command: ['git', 'status']\n"
        "Return code: 1\n"
        "Expected return code: 0\n"
        "Output: ('stdout', 'stderr')\n"
    )


@pytest.fixture
def popen_mock():
    popen = mock.Mock(spec=subprocess.Popen)
    popen.return_value.communicate.return_value = (b'stdout', b'stderr')
    return popen


@pytest.fixture
def makedirs_mock():
    return mock.Mock(spec=os.makedirs)


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


def test_run_substitutes_prefix(popen_mock, makedirs_mock):
    instance = PrefixedCommandRunner(
        'prefix', popen=popen_mock, makedirs=makedirs_mock,
    )
    ret = instance.run(['{prefix}bar', 'baz'], retcode=None)
    popen_mock.assert_called_once_with(
        ('prefix/bar', 'baz'),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert ret == (popen_mock.return_value.returncode, 'stdout', 'stderr')


PATH_TESTS = (
    ('foo', '', 'foo'),
    ('foo', 'bar', 'foo/bar'),
    ('foo/bar', '../baz', 'foo/baz'),
    ('./', 'bar', 'bar'),
    ('./', '', '.'),
    ('/tmp/foo', '/tmp/bar', '/tmp/bar'),
)


@pytest.mark.parametrize(('prefix', 'path_end', 'expected_output'), PATH_TESTS)
def test_path(prefix, path_end, expected_output):
    instance = PrefixedCommandRunner(prefix)
    ret = instance.path(path_end)
    assert ret == expected_output


def test_path_multiple_args():
    instance = PrefixedCommandRunner('foo')
    ret = instance.path('bar', 'baz')
    assert ret == 'foo/bar/baz'


@pytest.mark.parametrize(
    ('prefix', 'path_end', 'expected_output'),
    tuple(
        (prefix, path_end, expected_output + os.sep)
        for prefix, path_end, expected_output in PATH_TESTS
    ),
)
def test_from_command_runner(prefix, path_end, expected_output):
    first = PrefixedCommandRunner(prefix)
    second = PrefixedCommandRunner.from_command_runner(first, path_end)
    assert second.prefix_dir == expected_output


def test_from_command_runner_preserves_popen(popen_mock, makedirs_mock):
    first = PrefixedCommandRunner(
        'foo', popen=popen_mock, makedirs=makedirs_mock,
    )
    second = PrefixedCommandRunner.from_command_runner(first, 'bar')
    second.run(['foo/bar/baz'], retcode=None)
    popen_mock.assert_called_once_with(
        ('foo/bar/baz',),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    makedirs_mock.assert_called_once_with('foo/bar/')


def test_create_path_if_not_exists(in_tmpdir):
    instance = PrefixedCommandRunner('foo')
    assert not os.path.exists('foo')
    instance._create_path_if_not_exists()
    assert os.path.exists('foo')


def test_exists_does_not_exist(in_tmpdir):
    assert not PrefixedCommandRunner('.').exists('foo')


def test_exists_does_exist(in_tmpdir):
    os.mkdir('foo')
    assert PrefixedCommandRunner('.').exists('foo')


def test_raises_on_error(popen_mock, makedirs_mock):
    popen_mock.return_value.returncode = 1
    with pytest.raises(CalledProcessError):
        instance = PrefixedCommandRunner(
            '.', popen=popen_mock, makedirs=makedirs_mock,
        )
        instance.run(['foo'])
