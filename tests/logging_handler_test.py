from __future__ import unicode_literals

import mock

from pre_commit import color
from pre_commit.logging_handler import LoggingHandler


class FakeLogRecord(object):
    def __init__(self, message, levelname, levelno):
        self.message = message
        self.levelname = levelname
        self.levelno = levelno

    def getMessage(self):
        return self.message


def test_logging_handler_color():
    print_mock = mock.Mock()
    handler = LoggingHandler(True, print_mock)
    handler.emit(FakeLogRecord('hi', 'WARNING', 30))
    print_mock.assert_called_once_with(
        color.YELLOW + '[WARNING]' + color.NORMAL + ' hi\n',
    )


def test_logging_handler_no_color():
    print_mock = mock.Mock()
    handler = LoggingHandler(False, print_mock)
    handler.emit(FakeLogRecord('hi', 'WARNING', 30))
    print_mock.assert_called_once_with(
        '[WARNING] hi\n',
    )
