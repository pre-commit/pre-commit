from __future__ import annotations

import pytest

from pre_commit.errors import FatalError
from pre_commit.languages import haskell
from pre_commit.util import win_exe
from testing.language_helpers import run_language


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


def test_run_empty(tmp_path):
    with pytest.raises(FatalError) as excinfo:
        run_language(tmp_path, haskell, 'example')
    msg, = excinfo.value.args
    assert msg == 'Expected .cabal files or additional_dependencies'
