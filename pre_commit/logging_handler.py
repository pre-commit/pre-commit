from __future__ import unicode_literals

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
        super(LoggingHandler, self).__init__()
        self.use_color = use_color

    def emit(self, record):
        output.write_line(
            '{} {}'.format(
                color.format_color(
                    '[{}]'.format(record.levelname),
                    LOG_LEVEL_COLORS[record.levelname],
                    self.use_color,
                ),
                record.getMessage(),
            ),
        )


def add_logging_handler(*args, **kwargs):
    logger.addHandler(LoggingHandler(*args, **kwargs))
    logger.setLevel(logging.INFO)
