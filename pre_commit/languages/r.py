import contextlib
import os
import shlex
import shutil
from typing import Generator
from typing import Sequence
from typing import Tuple

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'renv'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def get_env_patch(venv: str) -> PatchesT:
    return (
        ('R_PROFILE_USER', os.path.join(venv, 'activate.R')),
    )


@contextlib.contextmanager
def in_env(
        prefix: Prefix,
        language_version: str,
) -> Generator[None, None, None]:
    envdir = _get_env_dir(prefix, language_version)
    with envcontext(get_env_patch(envdir)):
        yield


def _get_env_dir(prefix: Prefix, version: str) -> str:
    return prefix.path(helpers.environment_dir(ENVIRONMENT_DIR, version))


def _prefix_if_file_entry(
    entry: Sequence[str],
    prefix: Prefix,
) -> Sequence[str]:
    if entry[1] == '-e':
        return entry[1:]
    else:
        return (prefix.path(entry[1]),)


def _entry_validate(entry: Sequence[str]) -> None:
    """
    Allowed entries:
    # Rscript -e expr
    # Rscript path/to/file
    """
    if entry[0] != 'Rscript':
        raise ValueError('entry must start with `Rscript`.')

    if entry[1] == '-e':
        if len(entry) > 3:
            raise ValueError('You can supply at most one expression.')
    elif len(entry) > 2:
        raise ValueError(
            'The only valid syntax is `Rscript -e {expr}`',
            'or `Rscript path/to/hook/script`',
        )


def _cmd_from_hook(hook: Hook) -> Tuple[str, ...]:
    opts = ('--no-save', '--no-restore', '--no-site-file', '--no-environ')
    entry = shlex.split(hook.entry)
    _entry_validate(entry)

    return (
        *entry[:1], *opts,
        *_prefix_if_file_entry(entry, hook.prefix),
        *hook.args,
    )


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    env_dir = _get_env_dir(prefix, version)
    with clean_path_on_failure(env_dir):
        os.makedirs(env_dir, exist_ok=True)
        shutil.copy(prefix.path('renv.lock'), env_dir)
        cmd_output_b(
            'Rscript', '--vanilla', '-e',
            f"""\
            prefix_dir <- {prefix.prefix_dir!r}
            missing_pkgs <- setdiff(
                "renv", unname(installed.packages()[, "Package"])
            )
            options(
                repos = c(CRAN = "https://cran.rstudio.com"),
                renv.consent = TRUE
            )
            install.packages(missing_pkgs)
            renv::activate()
            renv::restore()
            activate_statement <- paste0(
              'renv::activate("', file.path(getwd()), '"); '
            )
            writeLines(activate_statement, 'activate.R')
            is_package <- tryCatch({{
                content_desc <- read.dcf(file.path(prefix_dir, 'DESCRIPTION'))
                suppressWarnings(unname(content_desc[,'Type']) == "Package")
                }},
                error = function(...) FALSE
            )
            if (is_package) {{
                renv::install(prefix_dir)
            }}
            """,
            cwd=env_dir,
        )
        if additional_dependencies:
            cmd_output_b(
                'Rscript', '-e',
                'renv::install(commandArgs(trailingOnly = TRUE))',
                *additional_dependencies,
                cwd=env_dir,
            )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:
    with in_env(hook.prefix, hook.language_version):
        return helpers.run_xargs(
            hook, _cmd_from_hook(hook), file_args, color=color,
        )
