from collections import OrderedDict

from pre_commit.meta_hooks import check_useless_excludes
from testing.fixtures import add_config_to_repo
from testing.fixtures import git_dir
from testing.util import cwd


def test_useless_exclude_global(capsys, tempdir_factory):
    config = OrderedDict((
        ('exclude', 'foo'),
        (
            'repos', [
                OrderedDict((
                    ('repo', 'meta'),
                    (
                        'hooks', (
                            OrderedDict((
                                ('id', 'check-useless-excludes'),
                            )),
                        ),
                    ),
                )),
            ],
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_useless_excludes.main(()) == 1

    out, _ = capsys.readouterr()
    assert "The global exclude pattern 'foo' does not match any files" in out


def test_useless_exclude_for_hook(capsys, tempdir_factory):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                    ('exclude', 'foo'),
                )),
            ),
        ),
    ))

    repo = git_dir(tempdir_factory)
    add_config_to_repo(repo, config)

    with cwd(repo):
        assert check_useless_excludes.main(()) == 1

    out, _ = capsys.readouterr()
    expected = (
        "The exclude pattern 'foo' for check-useless-excludes "
        "does not match any files"
    )
    assert expected in out


def test_no_excludes(capsys, tempdir_factory):
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
        assert check_useless_excludes.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''


def test_valid_exclude(capsys, tempdir_factory):
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
        assert check_useless_excludes.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''
