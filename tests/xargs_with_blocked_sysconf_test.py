from __future__ import annotations

import subprocess
import sys
import textwrap

# flake8: noqa: E501


# TODO
# import module without throwing exception
# create object without throwing exception
#  -- explicit _length
#  -- implicit _length


def test_import_module_without_throwing_exception_as_subprocess() -> None:
    """Import pre_commit.xargs in a subprocess even when os.sysconf is blocked.

    This test runs in a fresh subprocess where we can control os.sysconf
    BEFORE any imports happen, avoiding the conftest.py chicken/egg problem.

    With the current buggy implementation, this subprocess will crash
    (returncode != 0) because os.sysconf('SC_ARG_MAX') is called at import
    time and raises OSError.

    After the fix, the subprocess should succeed (returncode == 0).
    """
    script = textwrap.dedent("""
        import importlib
        import os
        from unittest import mock

        def main():
            # Force a posix-style environment.
            os.name = 'posix'

            # Block os.sysconf so that any SC_ARG_MAX lookup fails with OSError.
            with mock.patch.object(os, 'sysconf', side_effect=OSError('blocked')):
                # This should NOT raise with the fixed implementation.
                importlib.import_module('pre_commit.xargs')

        if __name__ == '__main__':
            main()
    """)

    proc = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd='/Users/michael/repos/pre-commit',
    )

    # Test-first: This test FAILS with current buggy behavior (subprocess crashes).
    # After fix, subprocess should succeed (returncode == 0).
    assert proc.returncode == 0, (
        f'Subprocess failed to import pre_commit.xargs when os.sysconf is blocked. '
        f'This exposes the bug: os.sysconf is called at import time. '
        f'stderr: {proc.stderr!r}'
    )

