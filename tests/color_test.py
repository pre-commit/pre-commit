from __future__ import unicode_literals

import os
import sys

import mock
import pytest

from pre_commit.color import format_color
from pre_commit.color import GREEN
from pre_commit.color import InvalidColorSetting
from pre_commit.color import use_color


@pytest.mark.parametrize(
    ('in_text', 'in_color', 'in_use_color', 'expected'), (
        ('foo', GREEN, True, '{}foo\033[0m'.format(GREEN)),
        ('foo', GREEN, False, 'foo'),
    ),
)
def test_format_color(in_text, in_color, in_use_color, expected):
    ret = format_color(in_text, in_color, in_use_color)
    assert ret == expected


def test_use_color_never():
    assert use_color('never') is False


def test_use_color_always():
    assert use_color('always') is True


def test_use_color_no_tty():
    with mock.patch.object(sys.stdout, 'isatty', return_value=False):
        assert use_color('auto') is False


def test_use_color_tty_with_color_support():
    with mock.patch.object(sys.stdout, 'isatty', return_value=True):
        with mock.patch('pre_commit.color.terminal_supports_color', True):
            assert use_color('auto') is True


def test_use_color_tty_without_color_support():
    with mock.patch.object(sys.stdout, 'isatty', return_value=True):
        with mock.patch('pre_commit.color.terminal_supports_color', False):
            assert use_color('auto') is False


def test_use_color_raises_if_given_shenanigans():
    with pytest.raises(InvalidColorSetting):
        use_color('herpaderp')


def test_no_color_env_unset():
    with mock.patch.dict(os.environ):
        if 'NO_COLOR' in os.environ:
            del os.environ['NO_COLOR']
        assert use_color('always') is True


def test_no_color_env_empty():
    with mock.patch.dict(os.environ, NO_COLOR=''):
        assert use_color('always') is True


def test_no_color_env_non_empty():
    with mock.patch.dict(os.environ, NO_COLOR=' '):
        assert use_color('always') is False
