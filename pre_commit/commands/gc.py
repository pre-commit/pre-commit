from __future__ import annotations

from pre_commit import output
from pre_commit.store import Store


def gc(store: Store) -> int:
    installs, clones = store.gc()
    output.write_line(f'{clones} clone(s) removed.')
    output.write_line(f'{installs} installs(s) removed.')
    return 0
