from __future__ import annotations

from unittest import mock

from pre_commit.languages import deno
from pre_commit.prefix import Prefix


def test_deno_run_hook(tmp_path):
    with mock.patch.object(
        deno.lang_base, 'run_xargs', return_value=(0, b''),
    ) as run_xargs:
        ret = deno.run_hook(
            Prefix(str(tmp_path)),
            'fmt --check',
            ('--unstable-sloppy-imports',),
            ('script.ts',),
            is_local=False,
            require_serial=True,
            color=False,
        )

    assert ret == (0, b'')
    run_xargs.assert_called_once_with(
        ('deno', 'fmt', '--check', '--unstable-sloppy-imports'),
        ('script.ts',),
        require_serial=True,
        color=False,
    )


def test_deno_health_check(monkeypatch, tmp_path):
    cmd_output = mock.Mock(return_value=(0, b'Deno 2.0.0', b''))
    monkeypatch.setattr(deno, 'cmd_output_b', cmd_output)

    assert deno.health_check(Prefix(str(tmp_path)), 'default') is None
    cmd_output.assert_called_once_with('deno', '--version', check=False)


def test_deno_health_check_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        deno, 'cmd_output_b', lambda *args, **kwargs: (127, b'', b''),
    )

    assert deno.health_check(
        Prefix(str(tmp_path)), 'default',
    ) == '`deno --version` returned 127'
