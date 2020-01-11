import logging

from pre_commit import color
from pre_commit.logging_handler import LoggingHandler


def _log_record(message, level):
    return logging.LogRecord('name', level, '', 1, message, {}, None)


def test_logging_handler_color(cap_out):
    handler = LoggingHandler(True)
    handler.emit(_log_record('hi', logging.WARNING))
    ret = cap_out.get()
    assert ret == color.YELLOW + '[WARNING]' + color.NORMAL + ' hi\n'


def test_logging_handler_no_color(cap_out):
    handler = LoggingHandler(False)
    handler.emit(_log_record('hi', logging.WARNING))
    assert cap_out.get() == '[WARNING] hi\n'
