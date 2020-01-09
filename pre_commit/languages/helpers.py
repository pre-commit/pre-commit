import multiprocessing
import os
import random

import pre_commit.constants as C
from pre_commit.util import cmd_output_b
from pre_commit.xargs import xargs

FIXED_RANDOM_SEED = 1542676186


def run_setup_cmd(prefix, cmd):
    cmd_output_b(*cmd, cwd=prefix.prefix_dir)


def environment_dir(ENVIRONMENT_DIR, language_version):
    if ENVIRONMENT_DIR is None:
        return None
    else:
        return f'{ENVIRONMENT_DIR}-{language_version}'


def assert_version_default(binary, version):
    if version != C.DEFAULT:
        raise AssertionError(
            f'For now, pre-commit requires system-installed {binary}',
        )


def assert_no_additional_deps(lang, additional_deps):
    if additional_deps:
        raise AssertionError(
            'For now, pre-commit does not support '
            'additional_dependencies for {}'.format(lang),
        )


def basic_get_default_version():
    return C.DEFAULT


def basic_healthy(prefix, language_version):
    return True


def no_install(prefix, version, additional_dependencies):
    raise AssertionError('This type is not installable')


def target_concurrency(hook):
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


def _shuffled(seq):
    """Deterministically shuffle identically under both py2 + py3."""
    fixed_random = random.Random()
    fixed_random.seed(FIXED_RANDOM_SEED, version=1)

    seq = list(seq)
    random.shuffle(seq, random=fixed_random.random)
    return seq


def run_xargs(hook, cmd, file_args, **kwargs):
    # Shuffle the files so that they more evenly fill out the xargs partitions,
    # but do it deterministically in case a hook cares about ordering.
    file_args = _shuffled(file_args)
    kwargs['target_concurrency'] = target_concurrency(hook)
    return xargs(cmd, file_args, **kwargs)
