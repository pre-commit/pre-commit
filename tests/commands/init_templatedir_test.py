import os.path
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.commands.init_templatedir import init_templatedir
from pre_commit.envcontext import envcontext
from pre_commit.util import cmd_output
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo
from testing.util import cmd_output_mocked_pre_commit_home
from testing.util import cwd
from testing.util import git_commit


def test_init_templatedir(tmpdir, tempdir_factory, store, cap_out):
    target = str(tmpdir.join('tmpl'))
    init_templatedir(C.CONFIG_FILE, store, target, hook_types=['pre-commit'])
    lines = cap_out.get().splitlines()
    assert lines[0].startswith('pre-commit installed at ')
    assert lines[1] == (
        '[WARNING] `init.templateDir` not set to the target directory'
    )
    assert lines[2].startswith(
        '[WARNING] maybe `git config --global init.templateDir',
    )

    with envcontext((('GIT_TEMPLATE_DIR', target),)):
        path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')

        with cwd(path):
            retcode, output = git_commit(
                fn=cmd_output_mocked_pre_commit_home,
                tempdir_factory=tempdir_factory,
            )
            assert retcode == 0
            assert 'Bash hook....' in output


def test_init_templatedir_already_set(tmpdir, tempdir_factory, store, cap_out):
    target = str(tmpdir.join('tmpl'))
    tmp_git_dir = git_dir(tempdir_factory)
    with cwd(tmp_git_dir):
        cmd_output('git', 'config', 'init.templateDir', target)
        init_templatedir(
            C.CONFIG_FILE, store, target, hook_types=['pre-commit'],
        )

    lines = cap_out.get().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith('pre-commit installed at')


def test_init_templatedir_not_set(tmpdir, store, cap_out):
    # set HOME to ignore the current `.gitconfig`
    with envcontext((('HOME', str(tmpdir)),)):
        with tmpdir.join('tmpl').ensure_dir().as_cwd():
            # we have not set init.templateDir so this should produce a warning
            init_templatedir(
                C.CONFIG_FILE, store, '.', hook_types=['pre-commit'],
            )

    lines = cap_out.get().splitlines()
    assert len(lines) == 3
    assert lines[1] == (
        '[WARNING] `init.templateDir` not set to the target directory'
    )


def test_init_templatedir_expanduser(tmpdir, tempdir_factory, store, cap_out):
    target = str(tmpdir.join('tmpl'))
    tmp_git_dir = git_dir(tempdir_factory)
    with cwd(tmp_git_dir):
        cmd_output('git', 'config', 'init.templateDir', '~/templatedir')
        with mock.patch.object(os.path, 'expanduser', return_value=target):
            init_templatedir(
                C.CONFIG_FILE, store, target, hook_types=['pre-commit'],
            )

    lines = cap_out.get().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith('pre-commit installed at')


def test_init_templatedir_hookspath_set(tmpdir, tempdir_factory, store):
    target = tmpdir.join('tmpl')
    tmp_git_dir = git_dir(tempdir_factory)
    with cwd(tmp_git_dir):
        cmd_output('git', 'config', '--local', 'core.hooksPath', 'hooks')
        init_templatedir(
            C.CONFIG_FILE, store, target, hook_types=['pre-commit'],
        )
    assert target.join('hooks/pre-commit').exists()


@pytest.mark.parametrize(
    ('skip', 'commit_retcode', 'commit_output_snippet'),
    (
        (True, 0, 'Skipping `pre-commit`.'),
        (False, 1, f'No {C.CONFIG_FILE} file was found'),
    ),
)
def test_init_templatedir_skip_on_missing_config(
    tmpdir,
    tempdir_factory,
    store,
    cap_out,
    skip,
    commit_retcode,
    commit_output_snippet,
):
    target = str(tmpdir.join('tmpl'))
    init_git_dir = git_dir(tempdir_factory)
    with cwd(init_git_dir):
        cmd_output('git', 'config', 'init.templateDir', target)
        init_templatedir(
            C.CONFIG_FILE,
            store,
            target,
            hook_types=['pre-commit'],
            skip_on_missing_config=skip,
        )

    lines = cap_out.get().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith('pre-commit installed at')

    with envcontext((('GIT_TEMPLATE_DIR', target),)):
        verify_git_dir = git_dir(tempdir_factory)

    with cwd(verify_git_dir):
        retcode, output = git_commit(
            fn=cmd_output_mocked_pre_commit_home,
            tempdir_factory=tempdir_factory,
            retcode=None,
        )

        assert retcode == commit_retcode
        assert commit_output_snippet in output
