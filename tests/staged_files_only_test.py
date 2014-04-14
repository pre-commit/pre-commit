import logging
import mock
import os.path
import pytest
import shutil
from plumbum import local

import pre_commit.constants as C
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.staged_files_only import staged_files_only
from testing.auto_namedtuple import auto_namedtuple
from testing.util import get_resource_path


FOO_CONTENTS = '\n'.join(('1', '2', '3', '4', '5', '6', '7', '8', ''))


def get_short_git_status():
    git_status = local['git']['status', '-s']()
    return dict(reversed(line.split()) for line in git_status.splitlines())


@pytest.yield_fixture
def foo_staged(empty_git_dir):
    with open('.gitignore', 'w') as gitignore_file:
        gitignore_file.write(C.HOOKS_WORKSPACE + '\n')
    local['git']['add', '.']()
    local['git']['commit', '-m', 'add gitignore']()

    with open('foo', 'w') as foo_file:
        foo_file.write(FOO_CONTENTS)
    local['git']['add', 'foo']()
    foo_filename = os.path.join(empty_git_dir, 'foo')
    yield auto_namedtuple(path=empty_git_dir, foo_filename=foo_filename)


@pytest.fixture
def cmd_runner():
    return PrefixedCommandRunner(C.HOOKS_WORKSPACE)


def _test_foo_state(path, foo_contents=FOO_CONTENTS, status='A'):
    assert os.path.exists(path.foo_filename)
    assert open(path.foo_filename).read() == foo_contents
    actual_status = get_short_git_status()['foo']
    assert status == actual_status


def test_foo_staged(foo_staged):
    _test_foo_state(foo_staged)


def test_foo_nothing_unstaged(foo_staged, cmd_runner):
    with staged_files_only(cmd_runner):
        _test_foo_state(foo_staged)
    _test_foo_state(foo_staged)


def test_foo_something_unstaged(foo_staged, cmd_runner):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write('herp\nderp\n')

    _test_foo_state(foo_staged, 'herp\nderp\n', 'AM')

    with staged_files_only(cmd_runner):
        _test_foo_state(foo_staged)

    _test_foo_state(foo_staged, 'herp\nderp\n', 'AM')


def test_foo_both_modify_non_conflicting(foo_staged, cmd_runner):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write(FOO_CONTENTS + '9\n')

    _test_foo_state(foo_staged, FOO_CONTENTS + '9\n', 'AM')

    with staged_files_only(cmd_runner):
        _test_foo_state(foo_staged)

        # Modify the file as part of the "pre-commit"
        with open(foo_staged.foo_filename, 'w') as foo_file:
            foo_file.write(FOO_CONTENTS.replace('1', 'a'))

        _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a'), 'AM')

    _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a') + '9\n', 'AM')


def test_foo_both_modify_conflicting(foo_staged, cmd_runner):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write(FOO_CONTENTS.replace('1', 'a'))

    _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a'), 'AM')

    with staged_files_only(cmd_runner):
        _test_foo_state(foo_staged)

        # Modify in the same place as the stashed diff
        with open(foo_staged.foo_filename, 'w') as foo_file:
            foo_file.write(FOO_CONTENTS.replace('1', 'b'))

        _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'b'), 'AM')

    _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a'), 'AM')


@pytest.yield_fixture
def img_staged(empty_git_dir):
    with open('.gitignore', 'w') as gitignore_file:
        gitignore_file.write(C.HOOKS_WORKSPACE + '\n')
    local['git']['add', '.']()
    local['git']['commit', '-m', 'add gitignore']()

    img_filename = os.path.join(empty_git_dir, 'img.jpg')
    shutil.copy(get_resource_path('img1.jpg'), img_filename)
    local['git']['add', 'img.jpg']()
    yield auto_namedtuple(path=empty_git_dir, img_filename=img_filename)


def _test_img_state(path, expected_file='img1.jpg', status='A'):
    assert os.path.exists(path.img_filename)
    assert (
        open(path.img_filename, 'rb').read() ==
        open(get_resource_path(expected_file), 'rb').read()
    )
    actual_status = get_short_git_status()['img.jpg']
    assert status == actual_status


def test_img_staged(img_staged):
    _test_img_state(img_staged)


def test_img_nothing_unstaged(img_staged, cmd_runner):
    with staged_files_only(cmd_runner):
        _test_img_state(img_staged)
    _test_img_state(img_staged)


def test_img_something_unstaged(img_staged, cmd_runner):
    shutil.copy(get_resource_path('img2.jpg'), img_staged.img_filename)

    _test_img_state(img_staged, 'img2.jpg', 'AM')

    with staged_files_only(cmd_runner):
        _test_img_state(img_staged)

    _test_img_state(img_staged, 'img2.jpg', 'AM')


def test_img_conflict(img_staged, cmd_runner):
    """Admittedly, this shouldn't happen, but just in case."""
    shutil.copy(get_resource_path('img2.jpg'), img_staged.img_filename)

    _test_img_state(img_staged, 'img2.jpg', 'AM')

    with staged_files_only(cmd_runner):
        _test_img_state(img_staged)
        shutil.copy(get_resource_path('img3.jpg'), img_staged.img_filename)
        _test_img_state(img_staged, 'img3.jpg', 'AM')

    _test_img_state(img_staged, 'img2.jpg', 'AM')


@pytest.yield_fixture
def submodule_with_commits(empty_git_dir):
    local['git']['commit', '--allow-empty', '-m', 'foo']()
    sha1 = local['git']['rev-parse', 'HEAD']().strip()
    local['git']['commit', '--allow-empty', '-m', 'bar']()
    sha2 = local['git']['rev-parse', 'HEAD']().strip()
    yield auto_namedtuple(path=empty_git_dir, sha1=sha1, sha2=sha2)


def checkout_submodule(sha):
    with local.cwd('sub'):
        local['git']['checkout', sha]()


@pytest.yield_fixture
def sub_staged(submodule_with_commits, empty_git_dir):
    local['git']['submodule', 'add', submodule_with_commits.path, 'sub']()
    checkout_submodule(submodule_with_commits.sha1)
    local['git']['add', 'sub']()
    yield auto_namedtuple(
        path=empty_git_dir,
        sub_path=os.path.join(empty_git_dir, 'sub'),
        submodule=submodule_with_commits,
    )


def _test_sub_state(path, sha='sha1', status='A'):
    assert os.path.exists(path.sub_path)
    with local.cwd(path.sub_path):
        actual_sha = local['git']['rev-parse', 'HEAD']().strip()
    assert actual_sha == getattr(path.submodule, sha)
    actual_status = get_short_git_status()['sub']
    assert actual_status == status


def test_sub_staged(sub_staged):
    _test_sub_state(sub_staged)


def test_sub_nothing_unstaged(sub_staged, cmd_runner):
    with staged_files_only(cmd_runner):
        _test_sub_state(sub_staged)
    _test_sub_state(sub_staged)


def test_sub_something_unstaged(sub_staged, cmd_runner):
    checkout_submodule(sub_staged.submodule.sha2)

    _test_sub_state(sub_staged, 'sha2', 'AM')

    with staged_files_only(cmd_runner):
        # This is different from others, we don't want to touch subs
        _test_sub_state(sub_staged, 'sha2', 'AM')

    _test_sub_state(sub_staged, 'sha2', 'AM')


@pytest.yield_fixture
def fake_logging_handler():
    class FakeHandler(logging.Handler):
        def __init__(self):
            logging.Handler.__init__(self)
            self.logs = []

        def emit(self, record):
            self.logs.append(record)  # pragma: no cover (only hit in failure)

    pre_commit_logger = logging.getLogger('pre_commit')
    original_level = pre_commit_logger.getEffectiveLevel()
    handler = FakeHandler()
    pre_commit_logger.addHandler(handler)
    pre_commit_logger.setLevel(logging.WARNING)
    yield handler
    pre_commit_logger.setLevel(original_level)
    pre_commit_logger.removeHandler(handler)


def test_diff_returns_1_no_diff_though(fake_logging_handler, foo_staged):
    cmd_runner = mock.Mock()
    cmd_runner.run.return_value = (1, '', '')
    cmd_runner.path.return_value = '.pre-commit-files_patch'
    with staged_files_only(cmd_runner):
        pass
    assert not fake_logging_handler.logs
