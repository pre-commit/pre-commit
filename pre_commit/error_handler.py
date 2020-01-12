import contextlib
import os.path
import sys
import traceback
from typing import Generator
from typing import Optional

import pre_commit.constants as C
from pre_commit import output
from pre_commit.store import Store


class FatalError(RuntimeError):
    pass


def _log_and_exit(msg: str, exc: BaseException, formatted: str) -> None:
    error_msg = b''.join((
        msg.encode(), b': ',
        type(exc).__name__.encode(), b': ',
        str(exc).encode(),
    ))
    output.write_line_b(error_msg)
    store = Store()
    log_path = os.path.join(store.directory, 'pre-commit.log')
    output.write_line(f'Check the log at {log_path}')

    with open(log_path, 'wb') as log:
        def _log_line(s: Optional[str] = None) -> None:
            output.write_line(s, stream=log)

        def _log_line_b(s: Optional[bytes] = None) -> None:
            output.write_line_b(s, stream=log)

        _log_line('### version information')
        _log_line()
        _log_line('```')
        _log_line(f'pre-commit version: {C.VERSION}')
        _log_line('sys.version:')
        for line in sys.version.splitlines():
            _log_line(f'    {line}')
        _log_line(f'sys.executable: {sys.executable}')
        _log_line(f'os.name: {os.name}')
        _log_line(f'sys.platform: {sys.platform}')
        _log_line('```')
        _log_line()

        _log_line('### error information')
        _log_line()
        _log_line('```')
        _log_line_b(error_msg)
        _log_line('```')
        _log_line()
        _log_line('```')
        _log_line(formatted)
        _log_line('```')
    raise SystemExit(1)


@contextlib.contextmanager
def error_handler() -> Generator[None, None, None]:
    try:
        yield
    except (Exception, KeyboardInterrupt) as e:
        if isinstance(e, FatalError):
            msg = 'An error has occurred'
        elif isinstance(e, KeyboardInterrupt):
            msg = 'Interrupted (^C)'
        else:
            msg = 'An unexpected error has occurred'
        _log_and_exit(msg, e, traceback.format_exc())
