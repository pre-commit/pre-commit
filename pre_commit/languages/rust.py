from __future__ import unicode_literals

import contextlib
import os.path

import toml

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'rustenv'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def get_env_patch(target_dir):
    return (
        (
            'PATH',
            (os.path.join(target_dir, 'release'), os.pathsep, Var('PATH')),
        ),
    )


@contextlib.contextmanager
def in_env(prefix):
    target_dir = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )
    with envcontext(get_env_patch(target_dir)):
        yield


def _add_dependencies(cargo_toml_path, additional_dependencies):
    with open(cargo_toml_path, 'r+') as f:
        cargo_toml = toml.load(f)
        for dep in additional_dependencies:
            name, _, spec = dep.partition(':')
            cargo_toml['dependencies'][name] = spec or '*'
        f.seek(0)
        toml.dump(cargo_toml, f)
        f.truncate()


def install_environment(prefix, version, additional_dependencies):
    helpers.assert_version_default('rust', version)
    directory = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )

    if len(additional_dependencies) > 0:
        _add_dependencies(prefix.path('Cargo.toml'), additional_dependencies)

    with clean_path_on_failure(directory):
        cmd_output(
            'cargo', 'build', '--release', '--bins', '--target-dir', directory,
            cwd=prefix.prefix_dir,
        )


def run_hook(prefix, hook, file_args):
    with in_env(prefix):
        return xargs(helpers.to_cmd(hook), file_args)
