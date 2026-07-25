from __future__ import annotations

from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.errors import FatalError
from pre_commit.languages import haskell
from pre_commit.prefix import Prefix
from pre_commit.util import win_exe
from testing.language_helpers import run_language


def test_install_uses_env_local_store(tmp_path):
    hook_dir = tmp_path.joinpath('hook dir')
    hook_dir.mkdir()
    hook_dir.joinpath('example.cabal').touch()
    prefix = Prefix(str(hook_dir))
    envdir = hook_dir.joinpath('hs_env-default')

    with mock.patch.object(lang_base, 'setup_cmd') as setup_cmd:
        haskell.install_environment(prefix, C.DEFAULT, ())

    assert setup_cmd.call_args_list == [
        mock.call(prefix, ('cabal', 'update')),
        mock.call(
            prefix,
            (
                'cabal', '--store-dir', str(envdir.joinpath('store')),
                'install',
                '--install-method', 'copy',
                '--installdir', str(envdir.joinpath('bin')),
                'example.cabal',
            ),
        ),
    ]


def test_run_example_executable(tmp_path):
    example_cabal = '''\
cabal-version:      2.4
name:               example
version:            0.1.0.0

executable example
    main-is:          Main.hs

    build-depends:    base >=4
    default-language: Haskell2010
'''
    main_hs = '''\
module Main where

main :: IO ()
main = putStrLn "Hello, Haskell!"
'''
    tmp_path.joinpath('example.cabal').write_text(example_cabal)
    tmp_path.joinpath('Main.hs').write_text(main_hs)

    result = run_language(tmp_path, haskell, 'example')
    assert result == (0, b'Hello, Haskell!\n')

    # should not symlink things into environments
    exe = tmp_path.joinpath(win_exe('hs_env-default/bin/example'))
    assert exe.is_file()
    assert not exe.is_symlink()


def test_run_dep(tmp_path):
    result = run_language(tmp_path, haskell, 'hello', deps=['hello'])
    assert result == (0, b'Hello, World!\n')
    assert tmp_path.joinpath('hs_env-default', 'store').is_dir()


def test_run_empty(tmp_path):
    with pytest.raises(FatalError) as excinfo:
        run_language(tmp_path, haskell, 'example')
    msg, = excinfo.value.args
    assert msg == 'Expected .cabal files or additional_dependencies'
