# encoding: utf-8
from __future__ import unicode_literals

from contextlib import contextmanager

import mock
import pytest

from pre_commit.file_classifier.classifier import _file_is_binary
from pre_commit.file_classifier.classifier import _guess_types_from_extension
from pre_commit.file_classifier.classifier import _guess_types_from_shebang
from pre_commit.file_classifier.classifier import _read_interpreter_from_shebang  # noqa
from pre_commit.file_classifier.classifier import classify
from pre_commit.git import GIT_MODE_EXECUTABLE
from pre_commit.git import GIT_MODE_FILE
from pre_commit.git import GIT_MODE_SUBMODULE
from pre_commit.git import GIT_MODE_SYMLINK


@contextmanager
def mock_open(read_data):
    # mock_open doesn't support reading binary data :\
    # https://bugs.python.org/issue23004
    with mock.patch('io.open') as m:
        mock_read = m.return_value.__enter__().read
        mock_read.return_value = read_data
        yield m


@pytest.mark.parametrize('path,data,mode,expected', [
    (
        'test.py',
        b'def main():\n    pass\n',
        GIT_MODE_FILE,
        ['file', 'text', 'python', 'nonexecutable'],
    ),
    (
        'Makefile',
        b'test:\n\ttac /etc/passwd\n',
        GIT_MODE_FILE,
        ['file', 'text', 'make', 'nonexecutable'],
    ),
    (
        'delete-everything',
        b'#!/bin/bash\nrm -rf /\n',
        GIT_MODE_EXECUTABLE,
        ['file', 'text', 'shell', 'executable'],
    ),
    (
        'bin/bash',
        b'\x7f\x45\x4c\x46\x02\x01\x01',
        GIT_MODE_EXECUTABLE,
        ['file', 'binary', 'executable'],
    ),
    (
        'modules/apache2',
        None,
        GIT_MODE_SUBMODULE,
        ['submodule'],
    ),
    (
        'some/secret',
        None,
        GIT_MODE_SYMLINK,
        ['symlink'],
    ),
])
def test_classify(path, data, mode, expected):
    with mock_open(data):
        assert set(classify(path, mode)) == set(expected)


def test_classify_invalid():
    # should raise ValueError if given a mode that it doesn't know about
    with pytest.raises(ValueError):
        classify('some_path', 9999)


@pytest.mark.parametrize('path,expected', [
    ('/hello/foo.py', ['python']),
    ('a/b/c/d/e.rb', ['ruby']),
    ('derp.sh', ['shell']),
    ('derp.tmpl.sh', ['shell']),

    ('', []),
    ('derpsh', []),
    ('\x7f\x45\x4c\x46\x02\x01\x01\x00\x00', []),
])
def test_guess_types_from_extension(path, expected):
    assert set(_guess_types_from_extension(path)) == set(expected)


@pytest.mark.parametrize('data,expected', [
    (b'#!/usr/bin/env python3\nasdf', ['python']),
    (b'#!/usr/bin/env /usr/bin/python2.7\nasdf', ['python']),
    (b'#!/bin/bash -euxm', ['shell']),
    (b'#!/bin/sh -euxm', ['shell']),

    (b'', []),
    (b'\x7f\x45\x4c\x46\x02\x01\x01\x00\x00', []),
])
def test_guess_types_from_shebang(data, expected):
    with mock_open(data):
        assert set(_guess_types_from_shebang('/etc/passwd')) == set(expected)


@pytest.mark.parametrize('data,expected', [
    (b'#!/usr/bin/env python3\nasdf', 'python3'),
    (b'#!/bin/bash -euxm', 'bash'),
    (b'#!/bin/bash -e -u -x -m', 'bash'),
    (b'#! /usr/bin/python    ', 'python'),

    (b'what is this', None),
    (b'', None),
    (b'#!\n/usr/bin/python', None),
    (b'\n#!/usr/bin/python', None),
    ('#!/usr/bin/énv python3\nasdf'.encode('utf8'), None),
    (b'#!         ', None),
    (b'\x7f\x45\x4c\x46\x02\x01\x01\x00\x00', None),
    (b'#!\x7f\x45\x4c\x46\x02\x01\x01\x00\x00', None),
])
def test_read_interpreter_from_shebang(data, expected):
    with mock_open(data) as m:
        assert _read_interpreter_from_shebang('/etc/passwd') == expected
        m.assert_called_once_with('/etc/passwd', 'rb')


@pytest.mark.parametrize('data,expected', [
    (b'hello world', False),
    (b'', False),
    ('éóñəå  ⊂(◉‿◉)つ(ノ≥∇≤)ノ'.encode('utf8'), False),
    ('¯\_(ツ)_/¯'.encode('utf8'), False),
    ('♪┏(・o･)┛♪┗ ( ･o･) ┓♪┏ ( ) ┛♪┗ (･o･ ) ┓♪┏(･o･)┛♪'.encode('utf8'), False),
    ('éóñå'.encode('latin1'), False),

    (b'hello world\x00', True),
    (b'\x7f\x45\x4c\x46\x02\x01\x01', True),  # first few bytes of /bin/bash
    (b'\x43\x92\xd9\x0f\xaf\x32\x2c', True),  # some /dev/urandom output
])
def test_file_is_binary(data, expected):
    with mock_open(data) as m:
        assert _file_is_binary('/etc/passwd') is expected
        m.assert_called_once_with('/etc/passwd', 'rb')
