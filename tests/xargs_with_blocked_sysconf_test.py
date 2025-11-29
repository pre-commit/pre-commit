"""Tests for pre_commit.xargs when os.sysconf is blocked in a sandbox environment."""
from __future__ import annotations

import subprocess
import sys
import textwrap

# flake8: noqa: E501

# Error message when os.sysconf is blocked in the test subprocess
BLOCKED_SYSCONF_ERROR = 'blocked'


def _create_import_test_script() -> str:
    """Create a Python script that tests importing pre_commit.xargs with blocked os.sysconf.

    This script must run in a subprocess (not in the main pytest process) because:
    1. We need to patch os.sysconf BEFORE any imports happen
    2. conftest.py already imports pre_commit.xargs in the main process
    3. A subprocess gives us a clean import state to test against
    """
    return textwrap.dedent(f"""
        import importlib
        import os
        from unittest import mock

        def main():
            # Force a posix-style environment.
            os.name = 'posix'

            # Block os.sysconf so that any SC_ARG_MAX lookup fails with OSError.
            with mock.patch.object(os, 'sysconf', side_effect=OSError('{BLOCKED_SYSCONF_ERROR}')):
                # This should NOT raise with the fixed implementation.
                importlib.import_module('pre_commit.xargs')

        if __name__ == '__main__':
            main()
    """)


def test_import_module_without_throwing_exception_as_subprocess() -> None:
    """Test that pre_commit.xargs can be imported when os.sysconf is blocked.

    This test uses a subprocess to avoid the conftest.py chicken/egg problem:
    - Phase 1 (this function): Sets up and runs a subprocess with blocked os.sysconf
    - Phase 2 (subprocess script): Attempts to import pre_commit.xargs in that environment

    With the current buggy implementation, the subprocess crashes because os.sysconf
    is called at import time. After the fix, the subprocess should succeed.
    """
    # Create the test script that will run in a subprocess
    script = _create_import_test_script()

    # Run the script in a fresh subprocess where we control os.sysconf
    proc = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd='/Users/michael/repos/pre-commit',
    )

    # Assert the subprocess succeeded (import worked without exception)
    # Test-first: This test FAILS with current buggy behavior (subprocess crashes).
    # After fix, subprocess should succeed (returncode == 0).
    assert proc.returncode == 0, (
        f'Subprocess failed to import pre_commit.xargs when os.sysconf is blocked. '
        f'This exposes the bug: os.sysconf is called at import time. '
        f'stderr: {proc.stderr!r}'
    )


def _create_xargs_test_script(use_explicit_max_length: bool = False) -> str:
    """Create a Python script that tests xargs.xargs() with blocked os.sysconf.

    This script must run in a subprocess (not in the main pytest process) because:
    1. We need to patch os.sysconf BEFORE any imports happen
    2. conftest.py already imports pre_commit.xargs in the main process
    3. A subprocess gives us a clean import state to test against

    Args:
        use_explicit_max_length: If True, pass explicit _max_length parameter.
                                 If False, rely on lazy evaluation of default.
    """
    max_length_param = (
        ', _max_length=4096' if use_explicit_max_length else ''
    )
    return textwrap.dedent(f"""
        import os
        import sys
        from unittest import mock

        def main():
            # Force a posix-style environment.
            os.name = 'posix'

            # Block os.sysconf so that any SC_ARG_MAX lookup fails with OSError.
            with mock.patch.object(os, 'sysconf', side_effect=OSError('{BLOCKED_SYSCONF_ERROR}')):
                # Import after patching os.sysconf
                from pre_commit import xargs

                # Test that xargs actually works - call it with a simple command
                retcode, stdout = xargs.xargs(
                    ('echo',),
                    ('hello', 'world'){max_length_param}
                )

                # Verify it succeeded and produced expected output
                if retcode != 0:
                    sys.exit(1)
                if b'hello world' not in stdout:
                    sys.exit(2)
                # Success - xargs worked despite blocked sysconf

        if __name__ == '__main__':
            main()
    """)


def test_xargs_without_max_length_when_sysconf_blocked_as_subprocess() -> None:
    """Test that xargs.xargs() works without _max_length when os.sysconf is blocked.

    This test verifies that lazy evaluation of _max_length handles blocked sysconf
    correctly. When _max_length is not provided, xargs should call
    _get_platform_max_length() at runtime, which should handle OSError gracefully.

    This test uses a subprocess to avoid the conftest.py chicken/egg problem.
    """
    # Create the test script that will run in a subprocess
    script = _create_xargs_test_script(use_explicit_max_length=False)

    # Run the script in a fresh subprocess where we control os.sysconf
    proc = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd='/Users/michael/repos/pre-commit',
    )

    # Assert the subprocess succeeded (xargs worked without exception)
    assert proc.returncode == 0, (
        f'Subprocess failed to run xargs.xargs() without _max_length when '
        f'os.sysconf is blocked. This exposes the bug: lazy evaluation of '
        f'_max_length calls _get_platform_max_length() which may fail. '
        f'stderr: {proc.stderr!r}'
    )


def test_xargs_with_explicit_max_length_when_sysconf_blocked_as_subprocess() -> None:
    """Test that xargs.xargs() works with explicit _max_length when os.sysconf is blocked.

    This test verifies that when _max_length is provided explicitly, xargs works
    correctly even when os.sysconf is blocked. This tests the code path where
    _get_platform_max_length() is never called.

    This test uses a subprocess to avoid the conftest.py chicken/egg problem.
    """
    # Create the test script that will run in a subprocess
    script = _create_xargs_test_script(use_explicit_max_length=True)

    # Run the script in a fresh subprocess where we control os.sysconf
    proc = subprocess.run(
        [sys.executable, '-c', script],
        capture_output=True,
        text=True,
        cwd='/Users/michael/repos/pre-commit',
    )

    # Assert the subprocess succeeded (xargs worked with explicit _max_length)
    assert proc.returncode == 0, (
        f'Subprocess failed to run xargs.xargs() with explicit _max_length when '
        f'os.sysconf is blocked. This should always work since _get_platform_max_length() '
        f'is never called. stderr: {proc.stderr!r}'
    )
