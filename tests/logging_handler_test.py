import __builtin__
import mock
import pytest

from pre_commit import color
from pre_commit.logging_handler import LoggingHandler


@pytest.yield_fixture
def print_mock():
    with mock.patch.object(__builtin__, 'print', autospec=True) as print_mock:
        yield print_mock


class FakeLogRecord(object):
    def __init__(self, message, levelname, levelno):
        self.message = message
        self.levelname = levelname
        self.levelno = levelno

    def getMessage(self):
        return self.message


def test_logging_handler_color(print_mock):
    handler = LoggingHandler(True)
    handler.emit(FakeLogRecord('hi', 'WARNING', 30))
    print_mock.assert_called_once_with(
        color.YELLOW + '[WARNING]' + color.NORMAL + ' hi',
    )


def test_logging_handler_no_color(print_mock):
    handler = LoggingHandler(False)
    handler.emit(FakeLogRecord('hi', 'WARNING', 30))
    print_mock.assert_called_once_with(
        '[WARNING] hi',
    )
