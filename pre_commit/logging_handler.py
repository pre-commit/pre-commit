from __future__ import print_function

import logging

from pre_commit import color


LOG_LEVEL_COLORS = {
    'DEBUG': '',
    'INFO': '',
    'WARNING': color.YELLOW,
    'ERROR': color.RED,
}


class LoggingHandler(logging.Handler):
    def __init__(self, use_color, print_fn=print):
        logging.Handler.__init__(self)
        self.use_color = use_color
        self.__print_fn = print_fn

    def emit(self, record):
        self.__print_fn(
            u'{0}{1}'.format(
                color.format_color(
                    '[{0}]'.format(record.levelname),
                    LOG_LEVEL_COLORS[record.levelname],
                    self.use_color,
                ) + ' ' if record.levelno >= logging.WARNING else '',
                record.getMessage(),
            )
        )
