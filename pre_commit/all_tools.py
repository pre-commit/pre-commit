from __future__ import annotations

from pre_commit.tool_base import Tool
from pre_commit.tools import go
from pre_commit.tools import node
from pre_commit.tools import python
from pre_commit.tools import rbenv
from pre_commit.tools import ruby
from pre_commit.tools import rust
from pre_commit.tools import rustup
from pre_commit.tools import uv


tools: dict[str, Tool] = {
    'go': go,
    'node': node,
    'python': python,
    'rbenv': rbenv,
    'ruby': ruby,
    'rust': rust,
    'rustup': rustup,
    'uv': uv,
}
