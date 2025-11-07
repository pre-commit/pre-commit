from __future__ import annotations

import sys
import urllib.request
from typing import IO

from pre_commit.constants import VERSION


def fetch(url: str) -> IO[bytes]:
    pyver = '.'.join(str(v) for v in sys.version_info[:3])
    req = urllib.request.Request(
        url,
        headers={'User-Agent': f'pre-commit/{VERSION} python/{pyver}'},
    )
    return urllib.request.urlopen(req)
