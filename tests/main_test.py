from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import os.path

import mock
import pytest

from pre_commit import main
from testing.auto_namedtuple import auto_namedtuple
from testing.util import cwd


FNS = (
    'autoupdate', 'clean', 'install', 'install_hooks', 'migrate_config', 'run',
    'sample_config', 'uninstall',
)
CMDS = tuple(fn.replace('_', '-') for fn in FNS)


@pytest.fixture
def mock_commands():
    mcks = {fn: mock.patch.object(main, fn).start() for fn in FNS}
    ret = auto_namedtuple(**mcks)
    yield ret
    for mck in ret:
        mck.stop()


class CalledExit(Exception):
    pass


@pytest.fixture
def argparse_exit_mock():
    with mock.patch.object(
        argparse.ArgumentParser, 'exit', side_effect=CalledExit,
    ) as exit_mock:
        yield exit_mock


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


def test_overall_help(mock_commands, argparse_exit_mock):
    with pytest.raises(CalledExit):
        main.main(['--help'])


def test_help_command(
        mock_commands, argparse_exit_mock, argparse_parse_args_spy,
):
    with pytest.raises(CalledExit):
        main.main(['help'])

    argparse_parse_args_spy.assert_has_calls([
        mock.call(['help']),
        mock.call(['--help']),
    ])


def test_help_other_command(
        mock_commands, argparse_exit_mock, argparse_parse_args_spy,
):
    with pytest.raises(CalledExit):
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


def test_help_cmd_in_empty_directory(
        mock_commands,
        tempdir_factory,
        argparse_exit_mock,
        argparse_parse_args_spy,
):
    path = tempdir_factory.get()

    with cwd(path):
        with pytest.raises(CalledExit):
            main.main(['help', 'run'])

    argparse_parse_args_spy.assert_has_calls([
        mock.call(['help', 'run']),
        mock.call(['run', '--help']),
    ])


def test_expected_fatal_error_no_git_repo(
        tempdir_factory, cap_out, mock_store_dir,
):
    with cwd(tempdir_factory.get()):
        with pytest.raises(SystemExit):
            main.main([])
    log_file = os.path.join(mock_store_dir, 'pre-commit.log')
    assert cap_out.get() == (
        'An error has occurred: FatalError: git failed. '
        'Is it installed, and are you in a Git repository directory?\n'
        'Check the log at {}\n'.format(log_file)
    )


def test_warning_on_tags_only(mock_commands, cap_out, mock_store_dir):
    main.main(('autoupdate', '--tags-only'))
    assert '--tags-only is the default' in cap_out.get()
