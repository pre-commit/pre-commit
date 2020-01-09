import contextlib
import logging

from pre_commit import color
from pre_commit import output


logger = logging.getLogger('pre_commit')

LOG_LEVEL_COLORS = {
    'DEBUG': '',
    'INFO': '',
    'WARNING': color.YELLOW,
    'ERROR': color.RED,
}


class LoggingHandler(logging.Handler):
    def __init__(self, use_color):
        super().__init__()
        self.use_color = use_color

    def emit(self, record):
        output.write_line(
            '{} {}'.format(
                color.format_color(
                    f'[{record.levelname}]',
                    LOG_LEVEL_COLORS[record.levelname],
                    self.use_color,
                ),
                record.getMessage(),
            ),
        )


@contextlib.contextmanager
def logging_handler(*args, **kwargs):
    handler = LoggingHandler(*args, **kwargs)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield
    finally:
        logger.removeHandler(handler)
