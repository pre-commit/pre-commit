#!/usr/bin/env python3
"""."""
import glob
import os
import pathlib
import re
import subprocess
import sys

GLOB_PATTERN = re.compile(r'([^:/\\])(?=[/\\]|$)')


def GetRealCasePath(path):
    """Convert a case preserving path to a case sensitive compatible path."""
    drive, tail = os.path.splitdrive(path)
    return next(
        iter(glob.glob(''.join((drive, re.sub(GLOB_PATTERN, r'[\1]', tail))))),
        path,
    )


def ConvertPath(path, prefix, drive_letter_case):
    """Convert a Windows path to a POSIX path."""
    if os.path.exists(path):
        path = GetRealCasePath(path)
        drive, tail = os.path.splitdrive(path)
        if drive and not os.path.isabs(path):
            drive, tail = os.path.splitdrive(os.path.abspath(path))
        if drive and drive[1:2] == r':':
            path = (
                prefix /
                drive_letter_case(drive[0]) /
                pathlib.PureWindowsPath(tail[1:]).as_posix()
            ).as_posix()
        else:
            path = pathlib.PureWindowsPath(path).as_posix()
    return path


def ConvertArgsWin32(*args):
    """Convert all path like arguments from Windows to POSIX."""
    path = os.path.abspath(os.environ.get('SystemRoot'))
    if not path or path[1:2] != r':':
        return args

    try:
        nix_path = subprocess.run(
            [args[0], '-c', 'pwd'],
            check=True,
            cwd=path,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        ).stdout.strip()
    except Exception:
        return args

    path = pathlib.PureWindowsPath(
        os.path.splitdrive(GetRealCasePath(path))[1],
    ).as_posix()
    prefix, nix_path, tail = (
        pathlib.PurePosixPath(nix_path).as_posix().partition(path)
    )
    if not prefix or nix_path != path or tail:
        return args

    drive_letter_case = (
        (lambda s: s.upper())
        if prefix[-1:].isupper()
        else (lambda s: s.lower())
        if prefix[-1:].islower()
        else (lambda s: s)
    )
    prefix = pathlib.PurePosixPath(prefix[0:-1])

    return [args[0]] + [
        ConvertPath(arg, prefix, drive_letter_case) for arg in args[1:]
    ]


ConvertArgs = (
    ConvertArgsWin32 if sys.platform == 'win32' else (lambda *args: args)
)

if __name__ == '__main__':
    print(*ConvertArgs(*sys.argv[1:]))
