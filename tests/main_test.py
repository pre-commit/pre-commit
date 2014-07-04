from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import mock
import pytest
from plumbum import local

from pre_commit import main
from testing.auto_namedtuple import auto_namedtuple


@pytest.yield_fixture
def mock_commands():
    with mock.patch.object(main, 'autoupdate') as autoupdate_mock:
        with mock.patch.object(main, 'clean') as clean_mock:
            with mock.patch.object(main, 'install') as install_mock:
                with mock.patch.object(main, 'uninstall') as uninstall_mock:
                    with mock.patch.object(main, 'run') as run_mock:
                        yield auto_namedtuple(
                            autoupdate_mock=autoupdate_mock,
                            clean_mock=clean_mock,
                            install_mock=install_mock,
                            uninstall_mock=uninstall_mock,
                            run_mock=run_mock,
                        )


class CalledExit(Exception):
    pass


@pytest.yield_fixture
def argparse_exit_mock():
    with mock.patch.object(
        argparse.ArgumentParser, 'exit', side_effect=CalledExit,
    ) as exit_mock:
        yield exit_mock


@pytest.yield_fixture
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


def test_install_command(mock_commands):
    main.main(['install'])
    assert mock_commands.install_mock.call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_uninstall_command(mock_commands):
    main.main(['uninstall'])
    assert mock_commands.uninstall_mock.call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_clean_command(mock_commands):
    main.main(['clean'])
    assert mock_commands.clean_mock.call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_autoupdate_command(mock_commands):
    main.main(['autoupdate'])
    assert mock_commands.autoupdate_mock.call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_run_command(mock_commands):
    main.main(['run'])
    assert mock_commands.run_mock.call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_no_commands_run_command(mock_commands):
    main.main([])
    assert mock_commands.run_mock.call_count == 1
    assert_only_one_mock_called(mock_commands)


def test_help_cmd_in_empty_directory(
        mock_commands,
        tmpdir_factory,
        argparse_exit_mock,
        argparse_parse_args_spy,
):
    path = tmpdir_factory.get()

    with local.cwd(path):
        with pytest.raises(CalledExit):
            main.main(['help', 'run'])

    argparse_parse_args_spy.assert_has_calls([
        mock.call(['help', 'run']),
        mock.call(['run', '--help']),
    ])
