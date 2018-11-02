from __future__ import unicode_literals

import multiprocessing
import os
import shlex

from pre_commit.util import cmd_output
from pre_commit.xargs import xargs


def run_setup_cmd(prefix, cmd):
    cmd_output(*cmd, cwd=prefix.prefix_dir, encoding=None)


def environment_dir(ENVIRONMENT_DIR, language_version):
    if ENVIRONMENT_DIR is None:
        return None
    else:
        return '{}-{}'.format(ENVIRONMENT_DIR, language_version)


def to_cmd(hook):
    return tuple(shlex.split(hook['entry'])) + tuple(hook['args'])


def assert_version_default(binary, version):
    if version != 'default':
        raise AssertionError(
            'For now, pre-commit requires system-installed {}'.format(binary),
        )


def assert_no_additional_deps(lang, additional_deps):
    if additional_deps:
        raise AssertionError(
            'For now, pre-commit does not support '
            'additional_dependencies for {}'.format(lang),
        )


def basic_get_default_version():
    return 'default'


def basic_healthy(prefix, language_version):
    return True


def no_install(prefix, version, additional_dependencies):
    raise AssertionError('This type is not installable')


def target_concurrency(hook):
    if hook['require_serial'] or 'PRE_COMMIT_NO_CONCURRENCY' in os.environ:
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


def run_xargs(hook, cmd, file_args):
    return xargs(cmd, file_args, target_concurrency=target_concurrency(hook))
