from collections import OrderedDict

from pre_commit.meta_hooks import check_files_matches_any
from pre_commit.util import cwd
from testing.fixtures import add_config_to_repo
from testing.fixtures import git_dir


def test_hook_excludes_everything(
        capsys, tempdir_factory, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                    ('exclude', '.pre-commit-config.yaml'),
                )),
            ),
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_files_matches_any.main(argv=[]) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_includes_nothing(
        capsys, tempdir_factory, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                    ('files', 'foo'),
                )),
            ),
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_files_matches_any.main(argv=[]) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_types_not_matched(
        capsys, tempdir_factory, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                    ('types', ['python']),
                )),
            ),
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_files_matches_any.main(argv=[]) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_types_excludes_everything(
        capsys, tempdir_factory, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                    ('exclude_types', ['yaml']),
                )),
            ),
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_files_matches_any.main(argv=[]) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_valid_includes(
        capsys, tempdir_factory, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                )),
            ),
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_files_matches_any.main(argv=[]) == 0

    out, _ = capsys.readouterr()
    assert out == ''
