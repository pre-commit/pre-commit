import multiprocessing
import os
import random
from typing import Any
from typing import List
from typing import NoReturn
from typing import Optional
from typing import overload
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING

import pre_commit.constants as C
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b
from pre_commit.xargs import xargs

if TYPE_CHECKING:
    from pre_commit.repository import Hook

FIXED_RANDOM_SEED = 1542676186


def run_setup_cmd(prefix: Prefix, cmd: Tuple[str, ...]) -> None:
    cmd_output_b(*cmd, cwd=prefix.prefix_dir)


@overload
def environment_dir(d: None, language_version: str) -> None: ...
@overload
def environment_dir(d: str, language_version: str) -> str: ...


def environment_dir(d: Optional[str], language_version: str) -> Optional[str]:
    if d is None:
        return None
    else:
        return f'{d}-{language_version}'


def assert_version_default(binary: str, version: str) -> None:
    if version != C.DEFAULT:
        raise AssertionError(
            f'For now, pre-commit requires system-installed {binary}',
        )


def assert_no_additional_deps(
        lang: str,
        additional_deps: Sequence[str],
) -> None:
    if additional_deps:
        raise AssertionError(
            'For now, pre-commit does not support '
            'additional_dependencies for {}'.format(lang),
        )


def basic_get_default_version() -> str:
    return C.DEFAULT


def basic_healthy(prefix: Prefix, language_version: str) -> bool:
    return True


def no_install(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> NoReturn:
    raise AssertionError('This type is not installable')


def target_concurrency(hook: 'Hook') -> int:
    if hook.require_serial or 'PRE_COMMIT_NO_CONCURRENCY' in os.environ:
        return 1
    else:
        # Travis appears to have a bunch of CPUs, but we can't use them all.
        if 'TRAVIS' in os.environ:
            return 2
        else:
            try:
                return multiprocessing.cpu_count()
            except NotImplementedError:
                return 1


def _shuffled(seq: Sequence[str]) -> List[str]:
    """Deterministically shuffle"""
    fixed_random = random.Random()
    fixed_random.seed(FIXED_RANDOM_SEED, version=1)

    seq = list(seq)
    random.shuffle(seq, random=fixed_random.random)
    return seq


def run_xargs(
        hook: 'Hook',
        cmd: Tuple[str, ...],
        file_args: Sequence[str],
        **kwargs: Any,
) -> Tuple[int, bytes]:
    # Shuffle the files so that they more evenly fill out the xargs partitions,
    # but do it deterministically in case a hook cares about ordering.
    file_args = _shuffled(file_args)
    kwargs['target_concurrency'] = target_concurrency(hook)
    return xargs(cmd, file_args, **kwargs)
