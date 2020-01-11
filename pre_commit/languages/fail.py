from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING

from pre_commit.languages import helpers

if TYPE_CHECKING:
    from pre_commit.repository import Hook

ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(
        hook: 'Hook',
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:
    out = hook.entry.encode('UTF-8') + b'\n\n'
    out += b'\n'.join(f.encode('UTF-8') for f in file_args) + b'\n'
    return 1, out
