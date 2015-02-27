from __future__ import unicode_literals

import logging
import sys

from pre_commit import color


LOG_LEVEL_COLORS = {
    'DEBUG': '',
    'INFO': '',
    'WARNING': color.YELLOW,
    'ERROR': color.RED,
}


class LoggingHandler(logging.Handler):
    def __init__(self, use_color, write=sys.stdout.write):
        logging.Handler.__init__(self)
        self.use_color = use_color
        self.__write = write

    def emit(self, record):
        self.__write(
            u'{0}{1}\n'.format(
                color.format_color(
                    '[{0}]'.format(record.levelname),
                    LOG_LEVEL_COLORS[record.levelname],
                    self.use_color,
                ) + ' ',
                record.getMessage(),
            )
        )
        sys.stdout.flush()
