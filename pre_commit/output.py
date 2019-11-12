from __future__ import unicode_literals

import sys
from functools import partial

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
        return start + '.' * (cols - len(start) - end_len - 1)
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


class NormalOutput(object):
    def __init__(self, mgr):
        self.mgr = mgr

    def write(self, *args, **kwargs):
        write(*args, **kwargs)

    def write_line(self, *args, **kwargs):
        write_line(*args, **kwargs)

    def process(self, status):
        pass


class LazyOutputProxy(NormalOutput):
    """
    Collect output call and repeat on fail
    """

    def __init__(self, mgr):
        super(LazyOutputProxy, self).__init__(mgr)
        self._calls = []
        self.status = None

    def write(self, *args, **kwargs):
        call = partial(write, *args, **kwargs)
        self._calls.append(call)

    def write_line(self, *args, **kwargs):
        call = partial(write_line, *args, **kwargs)
        self._calls.append(call)

    def process(self, status):
        self.status = status
        if status == 'Failed':
            self.mgr.close('Failed', color.RED)
            for call in self._calls:
                call()


class NormalMode(object):
    """
    Normal output - pass calls to real methods
    """
    output_proxy = NormalOutput

    def __init__(self, hooks, cols, clr):
        self._hooks = hooks
        self._cols = cols
        self._color = clr

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_output(self):
        return self.output_proxy(self)


class QuietMode(NormalMode):
    output_proxy = LazyOutputProxy

    def __init__(self, hooks, cols, clr):
        super(QuietMode, self).__init__(hooks, cols, clr)
        self._proxies = []
        self._closed = False
        self._msg = 'Running {} hooks'.format(len(hooks))

    def __enter__(self):
        write(get_hook_message(self._msg, end_len=7))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_output(self):
        """ Return new instance of collector """
        proxy = super(QuietMode, self).get_output()
        self._proxies.append(proxy)
        return proxy

    def close(self, status=None, print_color=None):
        if self._closed:
            return
        # TODO: Replace by constant
        if status is None:
            statuses = {x.status for x in self._proxies}
            if 'Passed' in statuses:
                print_color = color.GREEN
                status = 'Passed'
            else:
                print_color = color.YELLOW
                status = 'Skipped'

        self._summary(status, print_color)
        self._closed = True

    def _summary(self, status, end_color):
        """
        We have to clean line because statuses could have different length
        """
        write('\r')
        write(
            get_hook_message(
                self._msg,
                end_msg=status,
                end_color=end_color,
                use_color=self._color,
                cols=self._cols,
            ),
        )
