from __future__ import annotations

import io
import os.path
import urllib.request
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.envcontext import Var
from pre_commit.languages import rust
from pre_commit.prefix import Prefix
from pre_commit.store import _make_local_repo
from pre_commit.util import win_exe
from testing.language_helpers import run_language
from testing.util import cwd

ACTUAL_GET_DEFAULT_VERSION = rust.get_default_version.__wrapped__


@pytest.fixture
def cmd_output_b_mck():
    with mock.patch.object(rust, 'cmd_output_b') as mck:
        yield mck


def test_sets_system_when_rust_is_available(cmd_output_b_mck):
    cmd_output_b_mck.return_value = (0, b'', b'')
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


def test_uses_default_when_rust_is_not_available(cmd_output_b_mck):
    cmd_output_b_mck.return_value = (127, b'', b'error: not found')
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


def test_selects_system_even_if_rust_toolchain_toml(tmp_path):
    toolchain_toml = '[toolchain]\nchannel = "wtf"\n'
    tmp_path.joinpath('rust-toolchain.toml').write_text(toolchain_toml)

    with cwd(tmp_path):
        assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


def test_get_env_patch_non_system():
    envdir = os.path.join('path', 'to', 'envdir')
    patch = rust.get_env_patch(envdir, '1.87.0')
    assert patch == (
        ('PATH', (os.path.join(envdir, 'bin'), os.pathsep, Var('PATH'))),
        ('RUSTUP_HOME', os.path.join(envdir, 'rustup')),
        ('RUSTUP_TOOLCHAIN', '1.87.0'),
    )


def test_get_env_patch_default_resolves_to_stable():
    envdir = os.path.join('path', 'to', 'envdir')
    patch = rust.get_env_patch(envdir, C.DEFAULT)
    assert patch == (
        ('PATH', (os.path.join(envdir, 'bin'), os.pathsep, Var('PATH'))),
        ('RUSTUP_HOME', os.path.join(envdir, 'rustup')),
        ('RUSTUP_TOOLCHAIN', 'stable'),
    )


def test_get_env_patch_system_only_sets_path():
    envdir = os.path.join('path', 'to', 'envdir')
    patch = rust.get_env_patch(envdir, 'system')
    assert patch == (
        ('PATH', (os.path.join(envdir, 'bin'), os.pathsep, Var('PATH'))),
    )


def test_install_rust_with_toolchain_argv(tmp_path):
    # Pre-create envdir/bin/rustup so we skip the rustup-init download
    # branch and only check the toolchain-install argv.
    envdir = str(tmp_path)
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    bin_dir.joinpath(win_exe('rustup')).write_text('')

    with mock.patch.object(rust, 'cmd_output_b') as cmd_mck:
        rust.install_rust_with_toolchain('1.87.0', envdir)

    assert cmd_mck.call_args_list == [
        mock.call(
            'rustup', 'toolchain', 'install', '--no-self-update',
            '--profile', 'default', '1.87.0',
        ),
    ]


def test_install_rust_with_toolchain_rejects_system(tmp_path):
    # The function's self-envcontext would silently degrade to PATH-only
    # for 'system' (since `get_env_patch` skips RUSTUP_HOME there) and
    # let rustup-init write into the user's `~/.rustup`.  Defend against
    # a future caller forgetting to gate on `version != 'system'`.
    with pytest.raises(ValueError, match='does not support'):
        rust.install_rust_with_toolchain('system', str(tmp_path))


def test_install_rust_with_toolchain_bootstrap_argv(tmp_path):
    # Covers the rustup-init download branch (stubs `urllib.request.urlopen`
    # so this stays fast).  Without it, the bootstrap argv is only checked
    # transitively by the heavy integration test below.
    envdir = str(tmp_path)
    fake_payload = io.BytesIO(b'fake rustup-init binary')

    with mock.patch.object(
            urllib.request, 'urlopen', return_value=fake_payload,
    ), mock.patch.object(rust, 'cmd_output_b') as cmd_mck:
        rust.install_rust_with_toolchain('1.87.0', envdir)

    assert cmd_mck.call_args_list == [
        mock.call(
            mock.ANY, '-y', '--quiet', '--no-modify-path',
            '--default-toolchain', 'none',
        ),
        mock.call(
            'rustup', 'toolchain', 'install', '--no-self-update',
            '--profile', 'default', '1.87.0',
        ),
    ]
    init_path = cmd_mck.call_args_list[0].args[0]
    assert os.path.basename(init_path) == win_exe('rustup-init')


def test_install_rust_with_toolchain_pins_rustup_home(tmp_path):
    # The original bug was about *where* rustup writes -- argv tests
    # don't catch a regression where `RUSTUP_HOME` is dropped from
    # `get_env_patch`.  Capture `os.environ` per cmd_output_b call and
    # assert every rustup invocation sees our env-local RUSTUP_HOME.
    envdir = str(tmp_path)
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    bin_dir.joinpath(win_exe('rustup')).write_text('')

    seen: list[dict[str, str | None]] = []

    def capture(*args, **kwargs):
        seen.append({
            'RUSTUP_HOME': os.environ.get('RUSTUP_HOME'),
            'RUSTUP_TOOLCHAIN': os.environ.get('RUSTUP_TOOLCHAIN'),
            'PATH_HEAD': os.environ['PATH'].split(os.pathsep)[0],
        })
        return (0, b'', b'')

    with mock.patch.object(rust, 'cmd_output_b', side_effect=capture):
        rust.install_rust_with_toolchain('1.87.0', envdir)

    assert seen
    for entry in seen:
        assert entry['RUSTUP_HOME'] == os.path.join(envdir, 'rustup')
        assert entry['RUSTUP_TOOLCHAIN'] == '1.87.0'
        assert entry['PATH_HEAD'] == os.path.join(envdir, 'bin')


def test_install_rust_scopes_cargo_home_to_rustup_init(tmp_path):
    # `CARGO_HOME=envdir` must be set ONLY for the rustup-init invocation
    # (so rustup's proxy binaries land in envdir/bin/).  All other rustup
    # invocations must inherit the caller's CARGO_HOME so cargo can read
    # the user's `~/.cargo/{config,credentials}.toml` and the shared
    # registry cache.  Catches the regression where someone re-introduces
    # a global `CARGO_HOME=envdir` in `get_env_patch`.
    envdir = str(tmp_path)
    user_cargo_home = '/tmp/test-user-cargo-home'
    fake_payload = io.BytesIO(b'fake rustup-init binary')

    seen: list[dict[str, str | None]] = []

    def capture(*args, **kwargs):
        seen.append({
            'cmd': os.path.basename(args[0]),
            'CARGO_HOME': os.environ.get('CARGO_HOME'),
            'RUSTUP_HOME': os.environ.get('RUSTUP_HOME'),
        })
        return (0, b'', b'')

    with mock.patch.dict(
            os.environ, {'CARGO_HOME': user_cargo_home}, clear=False,
    ), mock.patch.object(
            urllib.request, 'urlopen', return_value=fake_payload,
    ), mock.patch.object(
            rust, 'cmd_output_b', side_effect=capture,
    ):
        rust.install_rust_with_toolchain('1.87.0', envdir)

    assert [e['cmd'] for e in seen] == [win_exe('rustup-init'), 'rustup']
    assert seen[0]['CARGO_HOME'] == envdir
    assert seen[1]['CARGO_HOME'] == user_cargo_home
    assert seen[0]['RUSTUP_HOME'] == os.path.join(envdir, 'rustup')
    assert seen[1]['RUSTUP_HOME'] == os.path.join(envdir, 'rustup')


def _populate_v1_envdir(tmp_path, version):
    # Mimic an env built by the no-system-rustup branch of the previous
    # layout: rustup-init dropped `rustup`, `cargo`, `rustc` proxies into
    # envdir/bin/, but the toolchain went to a temp dir that's now gone.
    envdir = tmp_path.joinpath(f'rustenv-{version}')
    bin_dir = envdir.joinpath('bin')
    bin_dir.mkdir(parents=True)
    for exe in ('rustup', 'cargo', 'rustc'):
        bin_dir.joinpath(win_exe(exe)).write_text('')
    return envdir


def test_health_check_detects_old_layout(tmp_path):
    # Migration cover: envs built by the previous layout have envdir/bin/
    # populated but no `envdir/rustup/`.  Without this check, pre-commit
    # would reuse them and the rustup proxy would silently auto-install
    # the toolchain into our (newly-pinned but empty) RUSTUP_HOME with
    # the user's default profile -- exactly the bug class this PR fixes.
    _populate_v1_envdir(tmp_path, '1.87.0')
    # NOTE: envdir/rustup/ deliberately absent.

    err = rust.health_check(Prefix(str(tmp_path)), '1.87.0')
    assert err is not None and 'missing rust toolchain' in err


def test_health_check_detects_wrong_toolchain(tmp_path):
    # If the user changes `language_version` after install (e.g. 1.87.0
    # -> stable), the env has *a* toolchain but not the configured one.
    # Without this check the rustup proxy would auto-install the requested
    # toolchain at runtime with the user's globally-set profile, dropping
    # rustfmt/clippy on CI images that default to `minimal`.
    envdir = _populate_v1_envdir(tmp_path, '1.87.0')
    envdir.joinpath(
        'rustup', 'toolchains', 'stable-x86_64-unknown-linux-gnu',
    ).mkdir(parents=True)

    err = rust.health_check(Prefix(str(tmp_path)), '1.87.0')
    assert err is not None and 'missing rust toolchain 1.87.0' in err


def _make_hello_world(tmp_path):
    src_dir = tmp_path.joinpath('src')
    src_dir.mkdir()
    src_dir.joinpath('main.rs').write_text(
        'fn main() {\n'
        '    println!("Hello, world!");\n'
        '}\n',
    )
    tmp_path.joinpath('Cargo.toml').write_text(
        '[package]\n'
        'name = "hello_world"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n',
    )


def test_bootstrapped_rustfmt_runs(tmp_path):
    # End-to-end bug repro: a `language: rust` + `rustfmt` hook on a
    # machine with no rust must bootstrap a toolchain that persists past
    # install and is reachable at hook-run time.
    _make_hello_world(tmp_path)

    bad_rs = tmp_path.joinpath('src', 'main.rs')
    bad_rs.write_text('fn main() {\nprintln!("hi");\n}\n')

    ret = run_language(
        tmp_path, rust, 'rustfmt',
        version='1.87.0', file_args=(str(bad_rs),),
    )
    assert ret == (0, b'')
    assert bad_rs.read_text() == 'fn main() {\n    println!("hi");\n}\n'

    envdir = tmp_path.joinpath('rustenv-1.87.0')
    assert envdir.joinpath('bin', win_exe('rustup')).is_file()
    toolchains = list(envdir.joinpath('rustup', 'toolchains').iterdir())
    assert len(toolchains) == 1, toolchains
    assert toolchains[0].joinpath('bin', win_exe('rustfmt')).exists()


@pytest.mark.parametrize('dep', ('cli:shellharden:4.2.0', 'cli:shellharden'))
def test_rust_cli_additional_dependencies(tmp_path, dep):
    _make_local_repo(str(tmp_path))

    t_sh = tmp_path.joinpath('t.sh')
    t_sh.write_text('echo $hi\n')

    assert rust.get_default_version() == 'system'
    ret = run_language(
        tmp_path,
        rust,
        'shellharden --transform',
        deps=(dep,),
        args=(str(t_sh),),
    )
    assert ret == (0, b'echo "$hi"\n')


def test_run_lib_additional_dependencies(tmp_path):
    _make_hello_world(tmp_path)

    deps = ('shellharden:4.2.0', 'git-version')
    ret = run_language(tmp_path, rust, 'hello_world', deps=deps)
    assert ret == (0, b'Hello, world!\n')

    bin_dir = tmp_path.joinpath('rustenv-system', 'bin')
    assert bin_dir.is_dir()
    assert not bin_dir.joinpath('shellharden').exists()
    assert not bin_dir.joinpath('shellharden.exe').exists()
