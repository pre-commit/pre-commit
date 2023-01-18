from __future__ import annotations

import os.path
import shutil

import pytest

from pre_commit import envcontext
from pre_commit.languages import r
from pre_commit.prefix import Prefix
from pre_commit.store import _make_local_repo
from pre_commit.util import win_exe
from testing.language_helpers import run_language


def test_r_parsing_file_no_opts_no_args(tmp_path):
    cmd = r._cmd_from_hook(Prefix(str(tmp_path)), 'Rscript some-script.R', ())
    assert cmd == (
        'Rscript',
        '--no-save', '--no-restore', '--no-site-file', '--no-environ',
        str(tmp_path.joinpath('some-script.R')),
    )


def test_r_parsing_file_opts_no_args():
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(['Rscript', '--no-init', '/path/to/file'])

    msg, = excinfo.value.args
    assert msg == (
        'The only valid syntax is `Rscript -e {expr}`'
        'or `Rscript path/to/hook/script`'
    )


def test_r_parsing_file_no_opts_args(tmp_path):
    cmd = r._cmd_from_hook(
        Prefix(str(tmp_path)),
        'Rscript some-script.R',
        ('--no-cache',),
    )
    assert cmd == (
        'Rscript',
        '--no-save', '--no-restore', '--no-site-file', '--no-environ',
        str(tmp_path.joinpath('some-script.R')),
        '--no-cache',
    )


def test_r_parsing_expr_no_opts_no_args1(tmp_path):
    cmd = r._cmd_from_hook(Prefix(str(tmp_path)), "Rscript -e '1+1'", ())
    assert cmd == (
        'Rscript',
        '--no-save', '--no-restore', '--no-site-file', '--no-environ',
        '-e', '1+1',
    )


def test_r_parsing_expr_no_opts_no_args2():
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(['Rscript', '-e', '1+1', '-e', 'letters'])
    msg, = excinfo.value.args
    assert msg == 'You can supply at most one expression.'


def test_r_parsing_expr_opts_no_args2():
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(
            ['Rscript', '--vanilla', '-e', '1+1', '-e', 'letters'],
        )
    msg, = excinfo.value.args
    assert msg == (
        'The only valid syntax is `Rscript -e {expr}`'
        'or `Rscript path/to/hook/script`'
    )


def test_r_parsing_expr_args_in_entry2():
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(['Rscript', '-e', 'expr1', '--another-arg'])

    msg, = excinfo.value.args
    assert msg == 'You can supply at most one expression.'


def test_r_parsing_expr_non_Rscirpt():
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(['AnotherScript', '-e', '{{}}'])

    msg, = excinfo.value.args
    assert msg == 'entry must start with `Rscript`.'


def test_rscript_exec_relative_to_r_home():
    expected = os.path.join('r_home_dir', 'bin', win_exe('Rscript'))
    with envcontext.envcontext((('R_HOME', 'r_home_dir'),)):
        assert r._rscript_exec() == expected


def test_path_rscript_exec_no_r_home_set():
    with envcontext.envcontext((('R_HOME', envcontext.UNSET),)):
        assert r._rscript_exec() == 'Rscript'


def test_r_hook(tmp_path):
    renv_lock = '''\
{
  "R": {
    "Version": "4.0.3",
    "Repositories": [
      {
        "Name": "CRAN",
        "URL": "https://cloud.r-project.org"
      }
    ]
  },
  "Packages": {
    "renv": {
      "Package": "renv",
      "Version": "0.12.5",
      "Source": "Repository",
      "Repository": "CRAN",
      "Hash": "5c0cdb37f063c58cdab3c7e9fbb8bd2c"
    },
    "rprojroot": {
      "Package": "rprojroot",
      "Version": "1.0",
      "Source": "Repository",
      "Repository": "CRAN",
      "Hash": "86704667fe0860e4fec35afdfec137f3"
    }
  }
}
'''
    description = '''\
Package: gli.clu
Title: What the Package Does (One Line, Title Case)
Type: Package
Version: 0.0.0.9000
Authors@R:
    person(given = "First",
           family = "Last",
           role = c("aut", "cre"),
           email = "first.last@example.com",
           comment = c(ORCID = "YOUR-ORCID-ID"))
Description: What the package does (one paragraph).
License: `use_mit_license()`, `use_gpl3_license()` or friends to
    pick a license
Encoding: UTF-8
LazyData: true
Roxygen: list(markdown = TRUE)
RoxygenNote: 7.1.1
Imports:
    rprojroot
'''
    hello_world_r = '''\
stopifnot(
    packageVersion('rprojroot') == '1.0',
    packageVersion('gli.clu') == '0.0.0.9000'
)
cat("Hello, World, from R!\n")
'''

    tmp_path.joinpath('renv.lock').write_text(renv_lock)
    tmp_path.joinpath('DESCRIPTION').write_text(description)
    tmp_path.joinpath('hello-world.R').write_text(hello_world_r)
    renv_dir = tmp_path.joinpath('renv')
    renv_dir.mkdir()
    shutil.copy(
        os.path.join(
            os.path.dirname(__file__),
            '../../pre_commit/resources/empty_template_activate.R',
        ),
        renv_dir.joinpath('activate.R'),
    )

    expected = (0, b'Hello, World, from R!\n')
    assert run_language(tmp_path, r, 'Rscript hello-world.R') == expected


def test_r_inline(tmp_path):
    _make_local_repo(str(tmp_path))

    cmd = '''\
Rscript -e '
    stopifnot(packageVersion("rprojroot") == "1.0")
    cat(commandArgs(trailingOnly = TRUE), "from R!\n", sep=", ")
'
'''

    ret = run_language(
        tmp_path,
        r,
        cmd,
        deps=('rprojroot@1.0',),
        args=('hi', 'hello'),
    )
    assert ret == (0, b'hi, hello, from R!\n')
