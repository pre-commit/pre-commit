from pre_commit.meta_hooks import check_hooks_apply
from testing.fixtures import add_config_to_repo
from testing.fixtures import git_dir
from testing.util import cwd


def test_hook_excludes_everything(capsys, tempdir_factory, mock_store_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [
                    {
                        'id': 'check-useless-excludes',
                        'exclude': '.pre-commit-config.yaml',
                    },
                ],
            },
        ],
    }

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_includes_nothing(capsys, tempdir_factory, mock_store_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [
                    {
                        'id': 'check-useless-excludes',
                        'files': 'foo',
                    },
                ],
            },
        ],
    }

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_types_not_matched(capsys, tempdir_factory, mock_store_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [
                    {
                        'id': 'check-useless-excludes',
                        'types': ['python'],
                    },
                ],
            },
        ],
    }

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_types_excludes_everything(
        capsys, tempdir_factory, mock_store_dir,
):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [
                    {
                        'id': 'check-useless-excludes',
                        'exclude_types': ['yaml'],
                    },
                ],
            },
        ],
    }

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_valid_always_run(capsys, tempdir_factory, mock_store_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [
                    # Should not be reported as an error due to always_run
                    {
                        'id': 'check-useless-excludes',
                        'files': '^$',
                        'always_run': True,
                    },
                ],
            },
        ],
    }

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_hooks_apply.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''


def test_valid_language_fail(capsys, tempdir_factory, mock_store_dir):
    config = {
        'repos': [
            {
                'repo': 'local',
                'hooks': [
                    # Should not be reported as an error due to language: fail
                    {
                        'id': 'changelogs-rst',
                        'name': 'changelogs must be rst',
                        'entry': 'changelog filenames must end in .rst',
                        'language': 'fail',
                        'files': r'changelog/.*(?<!\.rst)$',
                    },
                ],
            },
        ],
    }

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_hooks_apply.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''
