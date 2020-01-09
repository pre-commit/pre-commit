import mock
import pytest

from pre_commit import color
from pre_commit import output


@pytest.mark.parametrize(
    'kwargs',
    (
        # both end_msg and end_len
        {'end_msg': 'end', 'end_len': 1, 'end_color': '', 'use_color': True},
        # Neither end_msg nor end_len
        {},
        # Neither color option for end_msg
        {'end_msg': 'end'},
        # No use_color for end_msg
        {'end_msg': 'end', 'end_color': ''},
        # No end_color for end_msg
        {'end_msg': 'end', 'use_color': ''},
    ),
)
def test_get_hook_message_raises(kwargs):
    with pytest.raises(ValueError):
        output.get_hook_message('start', **kwargs)


def test_case_with_end_len():
    ret = output.get_hook_message('start', end_len=5, cols=15)
    assert ret == 'start' + '.' * 4


def test_case_with_end_msg():
    ret = output.get_hook_message(
        'start',
        end_msg='end',
        end_color='',
        use_color=False,
        cols=15,
    )
    assert ret == 'start' + '.' * 6 + 'end' + '\n'


def test_case_with_end_msg_using_color():
    ret = output.get_hook_message(
        'start',
        end_msg='end',
        end_color=color.RED,
        use_color=True,
        cols=15,
    )
    assert ret == 'start' + '.' * 6 + color.RED + 'end' + color.NORMAL + '\n'


def test_case_with_postfix_message():
    ret = output.get_hook_message(
        'start',
        postfix='post ',
        end_msg='end',
        end_color='',
        use_color=False,
        cols=20,
    )
    assert ret == 'start' + '.' * 6 + 'post ' + 'end' + '\n'


def test_make_sure_postfix_is_not_colored():
    ret = output.get_hook_message(
        'start',
        postfix='post ',
        end_msg='end',
        end_color=color.RED,
        use_color=True,
        cols=20,
    )
    assert ret == (
        'start' + '.' * 6 + 'post ' + color.RED + 'end' + color.NORMAL + '\n'
    )


def test_output_write_writes():
    fake_stream = mock.Mock()
    output.write('hello world', fake_stream)
    assert fake_stream.write.call_count == 1
