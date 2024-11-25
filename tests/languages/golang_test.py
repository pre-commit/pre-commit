from __future__ import annotations

from unittest import mock

import pytest
import re_assert

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.commands.install_uninstall import install
from pre_commit.envcontext import envcontext
from pre_commit.languages import golang
from pre_commit.store import _make_local_repo
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from testing.fixtures import add_config_to_repo
from testing.fixtures import make_config_from_repo
from testing.language_helpers import run_language
from testing.util import cmd_output_mocked_pre_commit_home
from testing.util import cwd
from testing.util import git_commit


ACTUAL_GET_DEFAULT_VERSION = golang.get_default_version.__wrapped__


@pytest.fixture
def exe_exists_mck():
    with mock.patch.object(lang_base, 'exe_exists') as mck:
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
        version='1.21.1',
    )

    assert ret == 0
    assert out.startswith(b'go version go1.21.1')


def test_local_golang_additional_deps(tmp_path):
    _make_local_repo(str(tmp_path))

    ret = run_language(
        tmp_path,
        golang,
        'hello',
        deps=('golang.org/x/example/hello@latest',),
    )

    assert ret == (0, b'Hello, world!\n')


def test_golang_hook_still_works_when_gobin_is_set(tmp_path):
    with envcontext((('GOBIN', str(tmp_path.joinpath('gobin'))),)):
        test_golang_system(tmp_path)


def test_during_commit_all(tmp_path, tempdir_factory, store, in_git_dir):
    hook_dir = tmp_path.joinpath('hook')
    hook_dir.mkdir()
    _make_hello_world(hook_dir)
    hook_dir.joinpath('.pre-commit-hooks.yaml').write_text(
        '-   id: hello-world\n'
        '    name: hello world\n'
        '    entry: golang-hello-world\n'
        '    language: golang\n'
        '    always_run: true\n',
    )
    cmd_output('git', 'init', hook_dir)
    cmd_output('git', 'add', '.', cwd=hook_dir)
    git_commit(cwd=hook_dir)

    add_config_to_repo(in_git_dir, make_config_from_repo(hook_dir))

    assert not install(C.CONFIG_FILE, store, hook_types=['pre-commit'])

    git_commit(
        fn=cmd_output_mocked_pre_commit_home,
        tempdir_factory=tempdir_factory,
    )


def test_automatic_toolchain_switching(tmp_path):
    go_mod = '''\
module toolchain-version-test

go 1.23.1
'''
    main_go = '''\
package main

func main() {}
'''
    tmp_path.joinpath('go.mod').write_text(go_mod)
    mod_dir = tmp_path.joinpath('toolchain-version-test')
    mod_dir.mkdir()
    main_file = mod_dir.joinpath('main.go')
    main_file.write_text(main_go)

    with pytest.raises(CalledProcessError) as excinfo:
        run_language(
            path=tmp_path,
            language=golang,
            version='1.22.0',
            exe='golang-version-test',
        )

    assert 'go.mod requires go >= 1.23.1' in excinfo.value.stderr.decode()


def test_automatic_toolchain_switching_go_fmt(tmp_path, monkeypatch):
    go_mod_hook = '''\
module toolchain-version-test

go 1.22.0
'''
    go_mod = '''\
module toolchain-version-test

go 1.23.1
'''
    main_go = '''\
package main

func main() {}
'''
    hook_dir = tmp_path.joinpath('hook')
    hook_dir.mkdir()
    hook_dir.joinpath('go.mod').write_text(go_mod_hook)

    test_dir = tmp_path.joinpath('test')
    test_dir.mkdir()
    test_dir.joinpath('go.mod').write_text(go_mod)
    main_file = test_dir.joinpath('main.go')
    main_file.write_text(main_go)

    with cwd(test_dir):
        ret, out = run_language(
            path=hook_dir,
            language=golang,
            version='1.22.0',
            exe='go fmt',
            file_args=(str(main_file),),
        )

        assert ret == 1
        assert 'go.mod requires go >= 1.23.1' in out.decode()
