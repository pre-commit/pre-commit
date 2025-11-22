from __future__ import annotations

import sys

import pytest

from pre_commit.commands.hazmat import _cmd_filenames
from pre_commit.commands.hazmat import main
from testing.util import cwd


def test_cmd_filenames_no_dash_dash():
    with pytest.raises(SystemExit) as excinfo:
        _cmd_filenames(('no', 'dashdash', 'here'))
    msg, = excinfo.value.args
    assert msg == 'hazmat entry must end with `--`'


def test_cmd_filenames_no_filenames():
    cmd, filenames = _cmd_filenames(('hello', 'world', '--'))
    assert cmd == ('hello', 'world')
    assert filenames == ()


def test_cmd_filenames_some_filenames():
    cmd, filenames = _cmd_filenames(('hello', 'world', '--', 'f1', 'f2'))
    assert cmd == ('hello', 'world')
    assert filenames == ('f1', 'f2')


def test_cmd_filenames_multiple_dashdash():
    cmd, filenames = _cmd_filenames(('hello', '--', 'arg', '--', 'f1', 'f2'))
    assert cmd == ('hello', '--', 'arg')
    assert filenames == ('f1', 'f2')


def test_cd_unexpected_filename():
    with pytest.raises(SystemExit) as excinfo:
        main(('cd', 'subdir', 'cmd', '--', 'subdir/1', 'not-subdir/2'))
    msg, = excinfo.value.args
    assert msg == "unexpected file without prefix='subdir/': not-subdir/2"


def _norm(out):
    return out.replace('\r\n', '\n')


def test_cd(tmp_path, capfd):
    subdir = tmp_path.joinpath('subdir')
    subdir.mkdir()
    subdir.joinpath('a').write_text('a')
    subdir.joinpath('b').write_text('b')

    with cwd(tmp_path):
        ret = main((
            'cd', 'subdir',
            sys.executable, '-c',
            'import os; print(os.getcwd());'
            'import sys; [print(open(f).read()) for f in sys.argv[1:]]',
            '--',
            'subdir/a', 'subdir/b',
        ))

    assert ret == 0
    out, err = capfd.readouterr()
    assert _norm(out) == f'{subdir}\na\nb\n'
    assert err == ''


def test_ignore_exit_code(capfd):
    ret = main((
        'ignore-exit-code', sys.executable, '-c', 'raise SystemExit("bye")',
    ))
    assert ret == 0
    out, err = capfd.readouterr()
    assert out == ''
    assert _norm(err) == 'bye\n'


def test_n1(capfd):
    ret = main((
        'n1', sys.executable, '-c', 'import sys; print(sys.argv[1:])',
        '--',
        'foo', 'bar', 'baz',
    ))
    assert ret == 0
    out, err = capfd.readouterr()
    assert _norm(out) == "['foo']\n['bar']\n['baz']\n"
    assert err == ''


def test_n1_some_error_code():
    ret = main((
        'n1', sys.executable, '-c',
        'import sys; raise SystemExit(sys.argv[1] == "error")',
        '--',
        'ok', 'error', 'ok',
    ))
    assert ret == 1
