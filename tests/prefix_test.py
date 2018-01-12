from __future__ import unicode_literals

import os

import pytest

from pre_commit.prefix import Prefix


def norm_slash(*args):
    return tuple(x.replace('/', os.sep) for x in args)


@pytest.mark.parametrize(
    ('input', 'expected_prefix'), (
        norm_slash('.', './'),
        norm_slash('foo', 'foo/'),
        norm_slash('bar/', 'bar/'),
        norm_slash('foo/bar', 'foo/bar/'),
        norm_slash('foo/bar/', 'foo/bar/'),
    ),
)
def test_init_normalizes_path_endings(input, expected_prefix):
    instance = Prefix(input)
    assert instance.prefix_dir == expected_prefix


PATH_TESTS = (
    norm_slash('foo', '', 'foo'),
    norm_slash('foo', 'bar', 'foo/bar'),
    norm_slash('foo/bar', '../baz', 'foo/baz'),
    norm_slash('./', 'bar', 'bar'),
    norm_slash('./', '', '.'),
    norm_slash('/tmp/foo', '/tmp/bar', '/tmp/bar'),
)


@pytest.mark.parametrize(('prefix', 'path_end', 'expected_output'), PATH_TESTS)
def test_path(prefix, path_end, expected_output):
    instance = Prefix(prefix)
    ret = instance.path(path_end)
    assert ret == expected_output


def test_path_multiple_args():
    instance = Prefix('foo')
    ret = instance.path('bar', 'baz')
    assert ret == os.path.join('foo', 'bar', 'baz')


def test_exists_does_not_exist(tmpdir):
    assert not Prefix(str(tmpdir)).exists('foo')


def test_exists_does_exist(tmpdir):
    tmpdir.ensure('foo')
    assert Prefix(str(tmpdir)).exists('foo')
