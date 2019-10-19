from __future__ import unicode_literals

import sys

from pre_commit import color
from pre_commit import five
from pre_commit.util import noop_context


def get_hook_message(
        start,
        postfix='',
        end_msg=None,
        end_len=0,
        end_color=None,
        use_color=None,
        cols=80,
):
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
    if bool(end_msg) == bool(end_len):
        raise ValueError('Expected one of (`end_msg`, `end_len`)')
    if end_msg is not None and (end_color is None or use_color is None):
        raise ValueError(
            '`end_color` and `use_color` are required with `end_msg`',
        )

    if end_len:
        num_dots = cols - len(start) - end_len - 1
        if end_msg is None:
            return start, num_dots
        return start + '.' * num_dots
    else:
        return '{}{}{}{}\n'.format(
            start,
            '.' * (cols - len(start) - len(postfix) - len(end_msg) - 1),
            postfix,
            color.format_color(end_msg, end_color, use_color),
        )


stdout_byte_stream = getattr(sys.stdout, 'buffer', sys.stdout)


def write(s, stream=stdout_byte_stream):
    stream.write(five.to_bytes(s))
    stream.flush()


def write_line(s=None, stream=stdout_byte_stream, logfile_name=None):
    output_streams = [stream]
    if logfile_name:
        ctx = open(logfile_name, 'ab')
        output_streams.append(ctx)
    else:
        ctx = noop_context()

    with ctx:
        for output_stream in output_streams:
            if s is not None:
                output_stream.write(five.to_bytes(s))
            output_stream.write(b'\n')
            output_stream.flush()
