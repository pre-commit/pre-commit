import contextlib
import sys
from typing import IO
from typing import Optional
from typing import Union

from pre_commit import color
from pre_commit import five


def get_hook_message(
        start: str,
        postfix: str = '',
        end_msg: Optional[str] = None,
        end_len: int = 0,
        end_color: Optional[str] = None,
        use_color: Optional[bool] = None,
        cols: int = 80,
) -> str:
    """Prints a message for running a hook.

    This currently supports three approaches:

    # Print `start` followed by dots, leaving 6 characters at the end
    >>> print_hook_message('start', end_len=6)
    start...............................................................

    # Print `start` followed by dots with the end message colored if coloring
    # is specified and a newline afterwards
    >>> print_hook_message(
        'start',
        end_msg='end',
        end_color=color.RED,
        use_color=True,
    )
    start...................................................................end

    # Print `start` followed by dots, followed by the `postfix` message
    # uncolored, followed by the `end_msg` colored if specified and a newline
    # afterwards
    >>> print_hook_message(
        'start',
        postfix='postfix ',
        end_msg='end',
        end_color=color.RED,
        use_color=True,
    )
    start...........................................................postfix end
    """
    if end_len:
        assert end_msg is None, end_msg
        return start + '.' * (cols - len(start) - end_len - 1)
    else:
        assert end_msg is not None
        assert end_color is not None
        assert use_color is not None
        return '{}{}{}{}\n'.format(
            start,
            '.' * (cols - len(start) - len(postfix) - len(end_msg) - 1),
            postfix,
            color.format_color(end_msg, end_color, use_color),
        )


def write(s: str, stream: IO[bytes] = sys.stdout.buffer) -> None:
    stream.write(five.to_bytes(s))
    stream.flush()


def write_line(
        s: Union[None, str, bytes] = None,
        stream: IO[bytes] = sys.stdout.buffer,
        logfile_name: Optional[str] = None,
) -> None:
    with contextlib.ExitStack() as exit_stack:
        output_streams = [stream]
        if logfile_name:
            stream = exit_stack.enter_context(open(logfile_name, 'ab'))
            output_streams.append(stream)

        for output_stream in output_streams:
            if s is not None:
                output_stream.write(five.to_bytes(s))
            output_stream.write(b'\n')
            output_stream.flush()
