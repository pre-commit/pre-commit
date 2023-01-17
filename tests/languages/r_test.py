from __future__ import annotations

import os.path

import pytest

from pre_commit import envcontext
from pre_commit.languages import r
from pre_commit.prefix import Prefix
from pre_commit.util import win_exe


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
