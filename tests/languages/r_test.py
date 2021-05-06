import os.path

import pytest

from pre_commit.languages import r
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from tests.repository_test import _get_hook_no_install


def _test_r_parsing(
    tempdir_factory,
    store,
    hook_id,
    expected_hook_expr={},
    expected_args={},
    config={},
    expect_path_prefix=True,
):
    repo_path = 'r_hooks_repo'
    path = make_repo(tempdir_factory, repo_path)
    config = config or make_config_from_repo(path)
    hook = _get_hook_no_install(config, store, hook_id)
    ret = r._cmd_from_hook(hook)
    expected_cmd = 'Rscript'
    expected_opts = (
        '--no-save', '--no-restore', '--no-site-file', '--no-environ',
    )
    expected_path = os.path.join(
        hook.prefix.prefix_dir if expect_path_prefix else '',
        f'{hook_id}.R',
    )
    expected = (
        expected_cmd,
        *expected_opts,
        *(expected_hook_expr or (expected_path,)),
        *expected_args,
    )
    assert ret == expected


def test_r_parsing_file_no_opts_no_args(tempdir_factory, store):
    hook_id = 'parse-file-no-opts-no-args'
    _test_r_parsing(tempdir_factory, store, hook_id)


def test_r_parsing_file_opts_no_args(tempdir_factory, store):
    with pytest.raises(ValueError) as excinfo:
        r._entry_validate(['Rscript', '--no-init', '/path/to/file'])

    msg = excinfo.value.args
    assert msg == (
        'The only valid syntax is `Rscript -e {expr}`',
        'or `Rscript path/to/hook/script`',
    )


def test_r_parsing_file_no_opts_args(tempdir_factory, store):
    hook_id = 'parse-file-no-opts-args'
    expected_args = ['--no-cache']
    _test_r_parsing(
        tempdir_factory, store, hook_id, expected_args=expected_args,
    )


def test_r_parsing_expr_no_opts_no_args1(tempdir_factory, store):
    hook_id = 'parse-expr-no-opts-no-args-1'
    _test_r_parsing(
        tempdir_factory, store, hook_id, expected_hook_expr=('-e', '1+1'),
    )


def test_r_parsing_expr_no_opts_no_args2(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(['Rscript', '-e', '1+1', '-e', 'letters'])
    msg = execinfo.value.args
    assert msg == ('You can supply at most one expression.',)


def test_r_parsing_expr_opts_no_args2(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(
            [
                'Rscript', '--vanilla', '-e', '1+1', '-e', 'letters',
            ],
        )
    msg = execinfo.value.args
    assert msg == (
        'The only valid syntax is `Rscript -e {expr}`',
        'or `Rscript path/to/hook/script`',
    )


def test_r_parsing_expr_args_in_entry2(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(['Rscript', '-e', 'expr1', '--another-arg'])

    msg = execinfo.value.args
    assert msg == ('You can supply at most one expression.',)


def test_r_parsing_expr_non_Rscirpt(tempdir_factory, store):
    with pytest.raises(ValueError) as execinfo:
        r._entry_validate(['AnotherScript', '-e', '{{}}'])

    msg = execinfo.value.args
    assert msg == ('entry must start with `Rscript`.',)


def test_r_parsing_file_local(tempdir_factory, store):
    path = 'path/to/script.R'
    hook_id = 'local-r'
    config = {
        'repo': 'local',
        'hooks': [{
            'id': hook_id,
            'name': 'local-r',
            'entry': f'Rscript {path}',
            'language': 'r',
        }],
    }
    _test_r_parsing(
        tempdir_factory,
        store,
        hook_id=hook_id,
        expected_hook_expr=(path,),
        config=config,
        expect_path_prefix=False,
    )
