from __future__ import absolute_import
from __future__ import unicode_literals

from pre_commit.languages.helpers import file_args_to_stdin


def test_file_args_to_stdin_empty():
    assert file_args_to_stdin([]) == ''


def test_file_args_to_stdin_some():
    assert file_args_to_stdin(['foo', 'bar']) == 'foo\nbar\n'


def test_file_args_to_stdin_tuple():
    assert file_args_to_stdin(('foo', 'bar')) == 'foo\nbar\n'
