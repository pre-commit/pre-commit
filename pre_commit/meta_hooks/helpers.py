import pipes
import sys


def make_meta_entry(modname):
    """the hook `entry` is passed through `shlex.split()` by the command
    runner, so to prevent issues with spaces and backslashes (on Windows)
    it must be quoted here.
    """
    return '{} -m {}'.format(pipes.quote(sys.executable), modname)
