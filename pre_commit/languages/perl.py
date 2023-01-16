from __future__ import annotations

import contextlib
import os
import shlex
from typing import Generator
from typing import Sequence

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix

ENVIRONMENT_DIR = 'perl_env'
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check
run_hook = helpers.basic_run_hook


def get_env_patch(venv: str) -> PatchesT:
    return (
        ('PATH', (os.path.join(venv, 'bin'), os.pathsep, Var('PATH'))),
        ('PERL5LIB', os.path.join(venv, 'lib', 'perl5')),
        ('PERL_MB_OPT', f'--install_base {shlex.quote(venv)}'),
        (
            'PERL_MM_OPT', (
                f'INSTALL_BASE={shlex.quote(venv)} '
                f'INSTALLSITEMAN1DIR=none INSTALLSITEMAN3DIR=none'
            ),
        ),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:
    helpers.assert_version_default('perl', version)

    with in_env(prefix, version):
        helpers.run_setup_cmd(
            prefix, ('cpan', '-T', '.', *additional_dependencies),
        )
