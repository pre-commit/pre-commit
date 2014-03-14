
import functools

import pre_commit.clientlib.validate_config
import pre_commit.clientlib.validate_manifest
import pre_commit.run


def make_entry_point(entry_point_func):
    """Decorator which turns a function which takes sys.argv[1:] and returns
    an integer into an argumentless function which returns an integer.

    Args:
        entry_point_func - A function which takes an array representing argv
    """
    @functools.wraps(entry_point_func)
    def func():
        import sys
        return entry_point_func(sys.argv[1:])
    return func


pre_commit_func = make_entry_point(pre_commit.run.run)
validate_manifest_func = make_entry_point(pre_commit.clientlib.validate_manifest.run)
validate_config_func = make_entry_point(pre_commit.clientlib.validate_config.run)