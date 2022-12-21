from __future__ import annotations

import contextlib
import os.path
import re
import tempfile
import xml.etree.ElementTree
import zipfile
from typing import Generator
from typing import Sequence

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure

ENVIRONMENT_DIR = 'dotnetenv'
BIN_DIR = 'bin'

get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check


def get_env_patch(venv: str) -> PatchesT:
    return (
        ('PATH', (os.path.join(venv, BIN_DIR), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix) -> Generator[None, None, None]:
    directory = helpers.environment_dir(ENVIRONMENT_DIR, C.DEFAULT)
    envdir = prefix.path(directory)
    with envcontext(get_env_patch(envdir)):
        yield


@contextlib.contextmanager
def _nuget_config_no_sources() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        nuget_config = os.path.join(tmpdir, 'nuget.config')
        with open(nuget_config, 'w') as f:
            f.write(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<configuration>'
                '  <packageSources>'
                '    <clear />'
                '  </packageSources>'
                '</configuration>',
            )
        yield nuget_config


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    helpers.assert_version_default('dotnet', version)
    helpers.assert_no_additional_deps('dotnet', additional_dependencies)

    envdir = prefix.path(helpers.environment_dir(ENVIRONMENT_DIR, version))
    with clean_path_on_failure(envdir):
        build_dir = 'pre-commit-build'

        # Build & pack nupkg file
        helpers.run_setup_cmd(
            prefix,
            (
                'dotnet', 'pack',
                '--configuration', 'Release',
                '--output', build_dir,
            ),
        )

        nupkg_dir = prefix.path(build_dir)
        nupkgs = [x for x in os.listdir(nupkg_dir) if x.endswith('.nupkg')]

        if not nupkgs:
            raise AssertionError('could not find any build outputs to install')

        for nupkg in nupkgs:
            with zipfile.ZipFile(os.path.join(nupkg_dir, nupkg)) as f:
                nuspec, = (x for x in f.namelist() if x.endswith('.nuspec'))
                with f.open(nuspec) as spec:
                    tree = xml.etree.ElementTree.parse(spec)

            namespace = re.match(r'{.*}', tree.getroot().tag)
            if not namespace:
                raise AssertionError('could not parse namespace from nuspec')

            tool_id_element = tree.find(f'.//{namespace[0]}id')
            if tool_id_element is None:
                raise AssertionError('expected to find an "id" element')

            tool_id = tool_id_element.text
            if not tool_id:
                raise AssertionError('"id" element missing tool name')

            # Install to bin dir
            with _nuget_config_no_sources() as nuget_config:
                helpers.run_setup_cmd(
                    prefix,
                    (
                        'dotnet', 'tool', 'install',
                        '--configfile', nuget_config,
                        '--tool-path', os.path.join(envdir, BIN_DIR),
                        '--add-source', build_dir,
                        tool_id,
                    ),
                )

        # Clean the git dir, ignoring the environment dir
        clean_cmd = ('git', 'clean', '-ffxd', '-e', f'{ENVIRONMENT_DIR}-*')
        helpers.run_setup_cmd(prefix, clean_cmd)


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> tuple[int, bytes]:
    with in_env(hook.prefix):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
