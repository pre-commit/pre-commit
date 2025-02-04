from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Generator
from collections.abc import Sequence

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.languages import python
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'pipenv_env'
get_default_version = python.get_default_version
run_hook = python.run_hook

def _assert_pipfile_exists(prefix: Prefix) -> None:
    if not os.path.exists(os.path.join(prefix.prefix_dir, 'Pipfile')):
        raise AssertionError(
            '`language: pipenv` requires a Pipfile in the repository'
        )

def health_check(prefix: Prefix, version: str) -> str | None:
    _assert_pipfile_exists(prefix)
    directory = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    
    try:
        with in_env(prefix, version):
            cmd_output_b('pipenv', 'check')
        return None
    except Exception as e:
        return f'pipenv environment check failed: {e}'

@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    directory = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    env = python.get_env_patch(directory)
    with envcontext(env):
        yield

def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    _assert_pipfile_exists(prefix)
    directory = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    
    with in_env(prefix, version):
        # Initialize virtualenv if it doesn't exist
        if not os.path.exists(directory):
            python_version = version if version != C.DEFAULT else f"{sys.version_info[0]}.{sys.version_info[1]}"
            cmd_output_b('pipenv', '--python', python_version)
        
        # Install dependencies from Pipfile
        cmd_output_b('pipenv', 'install', '--dev')
        
        # Install additional dependencies if specified
        if additional_dependencies:
            cmd_output_b('pipenv', 'install', *additional_dependencies) 