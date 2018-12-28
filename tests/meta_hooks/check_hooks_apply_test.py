from pre_commit.meta_hooks import check_hooks_apply
from testing.fixtures import add_config_to_repo


def test_hook_excludes_everything(capsys, in_git_dir, mock_store_dir):
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

    assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_includes_nothing(capsys, in_git_dir, mock_store_dir):
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

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_types_not_matched(capsys, in_git_dir, mock_store_dir):
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

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_hook_types_excludes_everything(capsys, in_git_dir, mock_store_dir):
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

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_hooks_apply.main(()) == 1

    out, _ = capsys.readouterr()
    assert 'check-useless-excludes does not apply to this repository' in out


def test_valid_exceptions(capsys, in_git_dir, mock_store_dir):
    config = {
        'repos': [
            {
                'repo': 'local',
                'hooks': [
                    # applies to a file
                    {
                        'id': 'check-yaml',
                        'name': 'check yaml',
                        'entry': './check-yaml',
                        'language': 'script',
                        'files': r'\.yaml$',
                    },
                    # Should not be reported as an error due to language: fail
                    {
                        'id': 'changelogs-rst',
                        'name': 'changelogs must be rst',
                        'entry': 'changelog filenames must end in .rst',
                        'language': 'fail',
                        'files': r'changelog/.*(?<!\.rst)$',
                    },
                    # Should not be reported as an error due to always_run
                    {
                        'id': 'i-always-run',
                        'name': 'make check',
                        'entry': 'make check',
                        'language': 'system',
                        'files': '^$',
                        'always_run': True,
                    },
                ],
            },
        ],
    }

    add_config_to_repo(in_git_dir.strpath, config)

    assert check_hooks_apply.main(()) == 0

    out, _ = capsys.readouterr()
    assert out == ''
