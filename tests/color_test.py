import mock
import pytest
import sys

from pre_commit.color import format_color
from pre_commit.color import GREEN
from pre_commit.color import InvalidColorSetting
from pre_commit.color import use_color


@pytest.mark.parametrize(('in_text', 'in_color', 'in_use_color', 'expected'), (
    ('foo', GREEN, True, '{0}foo\033[0m'.format(GREEN)),
    ('foo', GREEN, False, 'foo'),
))
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


def test_use_color_tty():
    with mock.patch.object(sys.stdout, 'isatty', return_value=True):
        assert use_color('auto') is True


def test_use_color_raises_if_given_shenanigans():
    with pytest.raises(InvalidColorSetting):
        use_color('herpaderp')
