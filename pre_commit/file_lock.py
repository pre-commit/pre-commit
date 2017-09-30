from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import errno


try:  # pragma: no cover (windows)
    import msvcrt

    # https://docs.microsoft.com/en-us/cpp/c-runtime-library/reference/locking

    # on windows we lock "regions" of files, we don't care about the actual
    # byte region so we'll just pick *some* number here.
    _region = 0xffff

    @contextlib.contextmanager
    def _locked(fileno, blocked_cb):
        try:
            msvcrt.locking(fileno, msvcrt.LK_NBLCK, _region)
        except IOError:
            blocked_cb()
            while True:
                try:
                    msvcrt.locking(fileno, msvcrt.LK_LOCK, _region)
                except IOError as e:
                    # Locking violation. Returned when the _LK_LOCK or _LK_RLCK
                    # flag is specified and the file cannot be locked after 10
                    # attempts.
                    if e.errno != errno.EDEADLOCK:
                        raise
                else:
                    break

        try:
            yield
        finally:
            # From cursory testing, it seems to get unlocked when the file is
            # closed so this may not be necessary.
            # The documentation however states:
            # "Regions should be locked only briefly and should be unlocked
            # before closing a file or exiting the program."
            msvcrt.locking(fileno, msvcrt.LK_UNLCK, _region)
except ImportError:  # pragma: no cover (posix)
    import fcntl

    @contextlib.contextmanager
    def _locked(fileno, blocked_cb):
        try:
            fcntl.flock(fileno, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            blocked_cb()
            fcntl.flock(fileno, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fileno, fcntl.LOCK_UN)


@contextlib.contextmanager
def lock(path, blocked_cb):
    with open(path, 'a+') as f:
        with _locked(f.fileno(), blocked_cb):
            yield
