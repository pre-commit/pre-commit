from __future__ import annotations

from pre_commit import output
from pre_commit.store import Store


def gc(store: Store) -> int:
    output.write_line(f'{store.gc()} repo(s) removed.')
    return 0
