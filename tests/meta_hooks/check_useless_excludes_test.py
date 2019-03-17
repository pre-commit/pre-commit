from pre_commit.meta_hooks import check_useless_excludes
from testing.fixtures import add_config_to_repo


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
