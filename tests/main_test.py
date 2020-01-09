import argparse
import os.path

import mock
import pytest

import pre_commit.constants as C
from pre_commit import main
from pre_commit.error_handler import FatalError
from testing.auto_namedtuple import auto_namedtuple


@pytest.mark.parametrize(
    ('argv', 'expected'),
    (
        ((), ['f']),
        (('--f', 'x'), ['x']),
        (('--f', 'x', '--f', 'y'), ['x', 'y']),
    ),
)
def test_append_replace_default(argv, expected):
    parser = argparse.ArgumentParser()
    parser.add_argument('--f', action=main.AppendReplaceDefault, default=['f'])
    assert parser.parse_args(argv).f == expected


class Args:
    def __init__(self, **kwargs):
        kwargs.setdefault('command', 'help')
        kwargs.setdefault('config', C.CONFIG_FILE)
        self.__dict__.update(kwargs)


def test_adjust_args_and_chdir_not_in_git_dir(in_tmpdir):
    with pytest.raises(FatalError):
        main._adjust_args_and_chdir(Args())


def test_adjust_args_and_chdir_in_dot_git_dir(in_git_dir):
    with in_git_dir.join('.git').as_cwd(), pytest.raises(FatalError):
        main._adjust_args_and_chdir(Args())


def test_adjust_args_and_chdir_noop(in_git_dir):
    args = Args(command='run', files=['f1', 'f2'])
    main._adjust_args_and_chdir(args)
    assert os.getcwd() == in_git_dir
    assert args.config == C.CONFIG_FILE
    assert args.files == ['f1', 'f2']


def test_adjust_args_and_chdir_relative_things(in_git_dir):
    in_git_dir.join('foo/cfg.yaml').ensure()
    in_git_dir.join('foo').chdir()

    args = Args(command='run', files=['f1', 'f2'], config='cfg.yaml')
    main._adjust_args_and_chdir(args)
    assert os.getcwd() == in_git_dir
    assert args.config == os.path.join('foo', 'cfg.yaml')
    assert args.files == [os.path.join('foo', 'f1'), os.path.join('foo', 'f2')]


def test_adjust_args_and_chdir_non_relative_config(in_git_dir):
    in_git_dir.join('foo').ensure_dir().chdir()

    args = Args()
    main._adjust_args_and_chdir(args)
    assert os.getcwd() == in_git_dir
    assert args.config == C.CONFIG_FILE


def test_adjust_args_try_repo_repo_relative(in_git_dir):
    in_git_dir.join('foo').ensure_dir().chdir()

    args = Args(command='try-repo', repo='../foo', files=[])
    assert os.path.exists(args.repo)
    main._adjust_args_and_chdir(args)
    assert os.getcwd() == in_git_dir
    assert os.path.exists(args.repo)
    assert args.repo == 'foo'


FNS = (
    'autoupdate', 'clean', 'gc', 'install', 'install_hooks', 'migrate_config',
    'run', 'sample_config', 'uninstall',
)
CMDS = tuple(fn.replace('_', '-') for fn in FNS)


@pytest.fixture
def mock_commands():
    mcks = {fn: mock.patch.object(main, fn).start() for fn in FNS}
    ret = auto_namedtuple(**mcks)
    yield ret
    for mck in ret:
        mck.stop()


@pytest.fixture
def argparse_parse_args_spy():
    parse_args_mock = mock.Mock()

    original_parse_args = argparse.ArgumentParser.parse_args

    def fake_parse_args(self, args):
        # call our spy object
        parse_args_mock(args)
        return original_parse_args(self, args)

    with mock.patch.object(
        argparse.ArgumentParser, 'parse_args', fake_parse_args,
    ):
        yield parse_args_mock


def assert_only_one_mock_called(mock_objs):
    total_call_count = sum(mock_obj.call_count for mock_obj in mock_objs)
    assert total_call_count == 1


def test_overall_help(mock_commands):
    with pytest.raises(SystemExit):
        main.main(['--help'])


def test_help_command(mock_commands, argparse_parse_args_spy):
    with pytest.raises(SystemExit):
        main.main(['help'])

    argparse_parse_args_spy.assert_has_calls([
        mock.call(['help']),
        mock.call(['--help']),
    ])


def test_help_other_command(mock_commands, argparse_parse_args_spy):
    with pytest.raises(SystemExit):
        main.main(['help', 'run'])

    argparse_parse_args_spy.assert_has_calls([
        mock.call(['help', 'run']),
        mock.call(['run', '--help']),
    ])


@pytest.mark.parametrize('command', CMDS)
def test_all_cmds(command, mock_commands, mock_store_dir):
    main.main((command,))
    assert getattr(mock_commands, command.replace('-', '_')).call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_try_repo(mock_store_dir):
    with mock.patch.object(main, 'try_repo') as patch:
        main.main(('try-repo', '.'))
    assert patch.call_count == 1


def test_init_templatedir(mock_store_dir):
    with mock.patch.object(main, 'init_templatedir') as patch:
        main.main(('init-templatedir', 'tdir'))
    assert patch.call_count == 1


def test_help_cmd_in_empty_directory(
        in_tmpdir,
        mock_commands,
        argparse_parse_args_spy,
):
    with pytest.raises(SystemExit):
        main.main(['help', 'run'])

    argparse_parse_args_spy.assert_has_calls([
        mock.call(['help', 'run']),
        mock.call(['run', '--help']),
    ])


def test_expected_fatal_error_no_git_repo(in_tmpdir, cap_out, mock_store_dir):
    with pytest.raises(SystemExit):
        main.main([])
    log_file = os.path.join(mock_store_dir, 'pre-commit.log')
    cap_out_lines = cap_out.get().splitlines()
    assert (
        cap_out_lines[-2] ==
        'An error has occurred: FatalError: git failed. '
        'Is it installed, and are you in a Git repository directory?'
    )
    assert cap_out_lines[-1] == f'Check the log at {log_file}'
