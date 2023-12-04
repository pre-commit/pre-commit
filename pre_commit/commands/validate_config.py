from __future__ import annotations

from collections.abc import Sequence

from pre_commit import clientlib


def validate_config(filenames: Sequence[str]) -> int:
    ret = 0

    if not filenames:
        raise FileNotFoundError("No files found. Did you supply a config to validate? (E.g. pre-commit validate-config path/to/.pre-commit-config.yaml)")

    for filename in filenames:
        try:
            clientlib.load_config(filename)
        except clientlib.InvalidConfigError as e:
            print(e)
            ret = 1
    if ret == 0:
        formatted_filenames = "\n".join([filename for filename in filenames])
        print(f"The following configs were validated:\n{formatted_filenames}")
    return ret
