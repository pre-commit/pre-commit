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

