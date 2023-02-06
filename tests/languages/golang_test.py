from __future__ import annotations

from unittest import mock

import pytest
import re_assert

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.languages import golang
from pre_commit.languages import helpers
from pre_commit.store import _make_local_repo
from testing.language_helpers import run_language


ACTUAL_GET_DEFAULT_VERSION = golang.get_default_version.__wrapped__


@pytest.fixture
def exe_exists_mck():
    with mock.patch.object(helpers, 'exe_exists') as mck:
        yield mck


def test_golang_default_version_system_available(exe_exists_mck):
    exe_exists_mck.return_value = True
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


def test_golang_default_version_system_not_available(exe_exists_mck):
    exe_exists_mck.return_value = False
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


ACTUAL_INFER_GO_VERSION = golang._infer_go_version.__wrapped__


def test_golang_infer_go_version_not_default():
    assert ACTUAL_INFER_GO_VERSION('1.19.4') == '1.19.4'


def test_golang_infer_go_version_default():
    version = ACTUAL_INFER_GO_VERSION(C.DEFAULT)

    assert version != C.DEFAULT
    re_assert.Matches(r'^\d+\.\d+(?:\.\d+)?$').assert_matches(version)


def _make_hello_world(tmp_path):
    go_mod = '''\
module golang-hello-world

go 1.18

require github.com/BurntSushi/toml v1.1.0
'''
    go_sum = '''\
github.com/BurntSushi/toml v1.1.0 h1:ksErzDEI1khOiGPgpwuI7x2ebx/uXQNw7xJpn9Eq1+I=
github.com/BurntSushi/toml v1.1.0/go.mod h1:CxXYINrC8qIiEnFrOxCa7Jy5BFHlXnUU2pbicEuybxQ=
'''  # noqa: E501
    hello_world_go = '''\
package main


import (
        "fmt"
        "github.com/BurntSushi/toml"
)

type Config struct {
        What string
}

func main() {
        var conf Config
        toml.Decode("What = 'world'\\n", &conf)
        fmt.Printf("hello %v\\n", conf.What)
}
'''
    tmp_path.joinpath('go.mod').write_text(go_mod)
    tmp_path.joinpath('go.sum').write_text(go_sum)
    mod_dir = tmp_path.joinpath('golang-hello-world')
    mod_dir.mkdir()
    main_file = mod_dir.joinpath('main.go')
    main_file.write_text(hello_world_go)


def test_golang_system(tmp_path):
    _make_hello_world(tmp_path)

    ret = run_language(tmp_path, golang, 'golang-hello-world')
    assert ret == (0, b'hello world\n')


def test_golang_default_version(tmp_path):
    _make_hello_world(tmp_path)

    ret = run_language(
        tmp_path,
        golang,
        'golang-hello-world',
        version=C.DEFAULT,
    )
    assert ret == (0, b'hello world\n')


def test_golang_versioned(tmp_path):
    _make_local_repo(str(tmp_path))

    ret, out = run_language(
        tmp_path,
        golang,
        'go version',
        version='1.18.4',
    )

    assert ret == 0
    assert out.startswith(b'go version go1.18.4')


def test_local_golang_additional_deps(tmp_path):
    _make_local_repo(str(tmp_path))

    ret = run_language(
        tmp_path,
        golang,
        'hello',
        deps=('golang.org/x/example/hello@latest',),
    )

    assert ret == (0, b'Hello, Go examples!\n')


def test_golang_hook_still_works_when_gobin_is_set(tmp_path):
    with envcontext((('GOBIN', str(tmp_path.joinpath('gobin'))),)):
        test_golang_system(tmp_path)
