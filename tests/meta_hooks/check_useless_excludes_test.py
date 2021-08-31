from pre_commit import git
from pre_commit.meta_hooks import check_useless_excludes
from pre_commit.util import cmd_output
from testing.fixtures import add_config_to_repo
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.util import xfailif_windows


def test_useless_exclude_global(capsys, in_git_dir):
    config = {
        'exclude': 'foo',
        'repos': [
            {
                'repo': 'meta',
                'hooks': [{'id': 'check-useless-excludes'}],
            },
        ],
    }

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_useless_excludes.main(()) == 1

    out, _ = capsys.readouterr()
    out = out.strip()
    assert "The global exclude pattern 'foo' does not match any files" == out


def test_useless_exclude_for_hook(capsys, in_git_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [{'id': 'check-useless-excludes', 'exclude': 'foo'}],
            },
        ],
    }

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_useless_excludes.main(()) == 1

    out, _ = capsys.readouterr()
    out = out.strip()
    expected = (
        "The exclude pattern 'foo' for check-useless-excludes "
        'does not match any files'
    )
    assert expected == out


def test_useless_exclude_with_types_filter(capsys, in_git_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [
                    {
                        'id': 'check-useless-excludes',
                        'exclude': '.pre-commit-config.yaml',
                        'types': ['python'],
                    },
                ],
            },
        ],
    }

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_useless_excludes.main(()) == 1

    out, _ = capsys.readouterr()
    out = out.strip()
    expected = (
        "The exclude pattern '.pre-commit-config.yaml' for "
        'check-useless-excludes does not match any files'
    )
    assert expected == out


def test_no_excludes(capsys, in_git_dir):
    config = {
        'repos': [
            {
                'repo': 'meta',
                'hooks': [{'id': 'check-useless-excludes'}],
            },
        ],
    }

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_useless_excludes.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''


def test_valid_exclude(capsys, in_git_dir):
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

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_useless_excludes.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''


@xfailif_windows  # pragma: win32 no cover
def test_useless_excludes_broken_symlink(capsys, in_git_dir, tempdir_factory):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    config = make_config_from_repo(path)
    config['hooks'][0]['exclude'] = 'broken-symlink'
    add_config_to_repo(in_git_dir.strpath, config)

    in_git_dir.join('broken-symlink').mksymlinkto('DNE')
    cmd_output('git', 'add', 'broken-symlink')
    git.commit()

    assert check_useless_excludes.main(('.pre-commit-config.yaml',)) == 0

    out, _ = capsys.readouterr()
    assert out == ''
