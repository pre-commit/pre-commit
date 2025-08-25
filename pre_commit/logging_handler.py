from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Generator

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
    def __init__(self, use_color: bool) -> None:
        super().__init__()
        self.use_color = use_color

    def emit(self, record: logging.LogRecord) -> None:
        level_msg = color.format_color(
            f'[{record.levelname}]',
            LOG_LEVEL_COLORS[record.levelname],
            self.use_color,
        )
        output.write_line(f'{level_msg} {record.getMessage()}')


def _set_log_level(logger: logging.Logger) -> None:
    """Set the logger level via PRECOMMIT_LOGLEVEL env var. Default is INFO."""
    raw_level: str = os.environ.get('PRECOMMIT_LOGLEVEL', 'INFO')
    try:
        logger.setLevel(int(raw_level))  # user can provide an integer
    except ValueError:
        level = logging.getLevelName(raw_level)  # user can provide a name
        if isinstance(level, str) and level.startswith('Level '):
            logger.setLevel(logging.INFO)
            msg = f"Unknown PRECOMMIT_LOGLEVEL: {raw_level!r}"
            logger.warning(msg)
        else:
            logger.setLevel(level)


@contextlib.contextmanager
def logging_handler(use_color: bool) -> Generator[None]:
    handler = LoggingHandler(use_color)
    logger.addHandler(handler)
    _set_log_level(logger)
    try:
        yield
    finally:
        logger.removeHandler(handler)
