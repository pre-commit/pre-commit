from pre_commit import color
from pre_commit.logging_handler import LoggingHandler


class FakeLogRecord:
    def __init__(self, message, levelname, levelno):
        self.message = message
        self.levelname = levelname
        self.levelno = levelno

    def getMessage(self):
        return self.message


def test_logging_handler_color(cap_out):
    handler = LoggingHandler(True)
    handler.emit(FakeLogRecord('hi', 'WARNING', 30))
    ret = cap_out.get()
    assert ret == color.YELLOW + '[WARNING]' + color.NORMAL + ' hi\n'


def test_logging_handler_no_color(cap_out):
    handler = LoggingHandler(False)
    handler.emit(FakeLogRecord('hi', 'WARNING', 30))
    assert cap_out.get() == '[WARNING] hi\n'
