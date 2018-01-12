from __future__ import unicode_literals

import shlex

from pre_commit.util import cmd_output


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
