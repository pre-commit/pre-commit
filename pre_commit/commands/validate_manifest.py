from __future__ import annotations

from pre_commit import clientlib


def validate_manifest(filenames: list[str]) -> int:
    ret = 0

    for filename in filenames:
        try:
            clientlib.load_manifest(filename)
        except clientlib.InvalidManifestError as e:
            print(e)
            ret = 1

    return ret
