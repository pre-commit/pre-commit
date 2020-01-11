import itertools
import os.path
import shutil

import pytest

from pre_commit import git
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import git_dir
from testing.util import cwd
from testing.util import get_resource_path
from testing.util import git_commit


FOO_CONTENTS = '\n'.join(('1', '2', '3', '4', '5', '6', '7', '8', ''))


@pytest.fixture
def patch_dir(tempdir_factory):
    return tempdir_factory.get()


def get_short_git_status():
    git_status = cmd_output('git', 'status', '-s')[1]
    line_parts = [line.split() for line in git_status.splitlines()]
    return {v: k for k, v in line_parts}


@pytest.fixture
def foo_staged(in_git_dir):
    foo = in_git_dir.join('foo')
    foo.write(FOO_CONTENTS)
    cmd_output('git', 'add', 'foo')
    yield auto_namedtuple(path=in_git_dir.strpath, foo_filename=foo.strpath)


def _test_foo_state(
        path,
        foo_contents=FOO_CONTENTS,
        status='A',
        encoding='UTF-8',
):
    assert os.path.exists(path.foo_filename)
    with open(path.foo_filename, encoding=encoding) as f:
        assert f.read() == foo_contents
    actual_status = get_short_git_status()['foo']
    assert status == actual_status


def test_foo_staged(foo_staged):
    _test_foo_state(foo_staged)


def test_foo_nothing_unstaged(foo_staged, patch_dir):
    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)
    _test_foo_state(foo_staged)


def test_foo_something_unstaged(foo_staged, patch_dir):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write('herp\nderp\n')

    _test_foo_state(foo_staged, 'herp\nderp\n', 'AM')

    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)

    _test_foo_state(foo_staged, 'herp\nderp\n', 'AM')


def test_does_not_crash_patch_dir_does_not_exist(foo_staged, patch_dir):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write('hello\nworld\n')

    shutil.rmtree(patch_dir)
    with staged_files_only(patch_dir):
        pass


def test_something_unstaged_ext_diff_tool(foo_staged, patch_dir, tmpdir):
    diff_tool = tmpdir.join('diff-tool.sh')
    diff_tool.write('#!/usr/bin/env bash\necho "$@"\n')
    cmd_output('git', 'config', 'diff.external', diff_tool.strpath)
    test_foo_something_unstaged(foo_staged, patch_dir)


def test_foo_something_unstaged_diff_color_always(foo_staged, patch_dir):
    cmd_output('git', 'config', '--local', 'color.diff', 'always')
    test_foo_something_unstaged(foo_staged, patch_dir)


def test_foo_both_modify_non_conflicting(foo_staged, patch_dir):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write(FOO_CONTENTS + '9\n')

    _test_foo_state(foo_staged, FOO_CONTENTS + '9\n', 'AM')

    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)

        # Modify the file as part of the "pre-commit"
        with open(foo_staged.foo_filename, 'w') as foo_file:
            foo_file.write(FOO_CONTENTS.replace('1', 'a'))

        _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a'), 'AM')

    _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a') + '9\n', 'AM')


def test_foo_both_modify_conflicting(foo_staged, patch_dir):
    with open(foo_staged.foo_filename, 'w') as foo_file:
        foo_file.write(FOO_CONTENTS.replace('1', 'a'))

    _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a'), 'AM')

    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)

        # Modify in the same place as the stashed diff
        with open(foo_staged.foo_filename, 'w') as foo_file:
            foo_file.write(FOO_CONTENTS.replace('1', 'b'))

        _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'b'), 'AM')

    _test_foo_state(foo_staged, FOO_CONTENTS.replace('1', 'a'), 'AM')


@pytest.fixture
def img_staged(in_git_dir):
    img = in_git_dir.join('img.jpg')
    shutil.copy(get_resource_path('img1.jpg'), img.strpath)
    cmd_output('git', 'add', 'img.jpg')
    yield auto_namedtuple(path=in_git_dir.strpath, img_filename=img.strpath)


def _test_img_state(path, expected_file='img1.jpg', status='A'):
    assert os.path.exists(path.img_filename)
    with open(path.img_filename, 'rb') as f1:
        with open(get_resource_path(expected_file), 'rb') as f2:
            assert f1.read() == f2.read()
    actual_status = get_short_git_status()['img.jpg']
    assert status == actual_status


def test_img_staged(img_staged):
    _test_img_state(img_staged)


def test_img_nothing_unstaged(img_staged, patch_dir):
    with staged_files_only(patch_dir):
        _test_img_state(img_staged)
    _test_img_state(img_staged)


def test_img_something_unstaged(img_staged, patch_dir):
    shutil.copy(get_resource_path('img2.jpg'), img_staged.img_filename)

    _test_img_state(img_staged, 'img2.jpg', 'AM')

    with staged_files_only(patch_dir):
        _test_img_state(img_staged)

    _test_img_state(img_staged, 'img2.jpg', 'AM')


def test_img_conflict(img_staged, patch_dir):
    """Admittedly, this shouldn't happen, but just in case."""
    shutil.copy(get_resource_path('img2.jpg'), img_staged.img_filename)

    _test_img_state(img_staged, 'img2.jpg', 'AM')

    with staged_files_only(patch_dir):
        _test_img_state(img_staged)
        shutil.copy(get_resource_path('img3.jpg'), img_staged.img_filename)
        _test_img_state(img_staged, 'img3.jpg', 'AM')

    _test_img_state(img_staged, 'img2.jpg', 'AM')


@pytest.fixture
def submodule_with_commits(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        git_commit()
        rev1 = cmd_output('git', 'rev-parse', 'HEAD')[1].strip()
        git_commit()
        rev2 = cmd_output('git', 'rev-parse', 'HEAD')[1].strip()
        yield auto_namedtuple(path=path, rev1=rev1, rev2=rev2)


def checkout_submodule(rev):
    cmd_output('git', 'checkout', rev, cwd='sub')


@pytest.fixture
def sub_staged(submodule_with_commits, tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        cmd_output(
            'git', 'submodule', 'add', submodule_with_commits.path, 'sub',
        )
        checkout_submodule(submodule_with_commits.rev1)
        cmd_output('git', 'add', 'sub')
        yield auto_namedtuple(
            path=path,
            sub_path=os.path.join(path, 'sub'),
            submodule=submodule_with_commits,
        )


def _test_sub_state(path, rev='rev1', status='A'):
    assert os.path.exists(path.sub_path)
    with cwd(path.sub_path):
        actual_rev = cmd_output('git', 'rev-parse', 'HEAD')[1].strip()
    assert actual_rev == getattr(path.submodule, rev)
    actual_status = get_short_git_status()['sub']
    assert actual_status == status


def test_sub_staged(sub_staged):
    _test_sub_state(sub_staged)


def test_sub_nothing_unstaged(sub_staged, patch_dir):
    with staged_files_only(patch_dir):
        _test_sub_state(sub_staged)
    _test_sub_state(sub_staged)


def test_sub_something_unstaged(sub_staged, patch_dir):
    checkout_submodule(sub_staged.submodule.rev2)

    _test_sub_state(sub_staged, 'rev2', 'AM')

    with staged_files_only(patch_dir):
        # This is different from others, we don't want to touch subs
        _test_sub_state(sub_staged, 'rev2', 'AM')

    _test_sub_state(sub_staged, 'rev2', 'AM')


def test_stage_utf8_changes(foo_staged, patch_dir):
    contents = '\u2603'
    with open('foo', 'w', encoding='UTF-8') as foo_file:
        foo_file.write(contents)

    _test_foo_state(foo_staged, contents, 'AM')
    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)
    _test_foo_state(foo_staged, contents, 'AM')


def test_stage_non_utf8_changes(foo_staged, patch_dir):
    contents = 'ú'
    # Produce a latin-1 diff
    with open('foo', 'w', encoding='latin-1') as foo_file:
        foo_file.write(contents)

    _test_foo_state(foo_staged, contents, 'AM', encoding='latin-1')
    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)
    _test_foo_state(foo_staged, contents, 'AM', encoding='latin-1')


def test_non_utf8_conflicting_diff(foo_staged, patch_dir):
    """Regression test for #397"""
    # The trailing whitespace is important here, this triggers git to produce
    # an error message which looks like:
    #
    # ...patch1471530032:14: trailing whitespace.
    # [[unprintable character]][[space character]]
    # error: patch failed: foo:1
    # error: foo: patch does not apply
    #
    # Previously, the error message (though discarded immediately) was being
    # decoded with the UTF-8 codec (causing a crash)
    contents = 'ú \n'
    with open('foo', 'w', encoding='latin-1') as foo_file:
        foo_file.write(contents)

    _test_foo_state(foo_staged, contents, 'AM', encoding='latin-1')
    with staged_files_only(patch_dir):
        _test_foo_state(foo_staged)
        # Create a conflicting diff that will need to be rolled back
        with open('foo', 'w') as foo_file:
            foo_file.write('')
    _test_foo_state(foo_staged, contents, 'AM', encoding='latin-1')


def _write(b):
    with open('foo', 'wb') as f:
        f.write(b)


def assert_no_diff():
    tree = cmd_output('git', 'write-tree')[1].strip()
    cmd_output('git', 'diff-index', tree, '--exit-code')


bool_product = tuple(itertools.product((True, False), repeat=2))


@pytest.mark.parametrize(('crlf_before', 'crlf_after'), bool_product)
@pytest.mark.parametrize('autocrlf', ('true', 'false', 'input'))
def test_crlf(in_git_dir, patch_dir, crlf_before, crlf_after, autocrlf):
    cmd_output('git', 'config', '--local', 'core.autocrlf', autocrlf)

    before, after = b'1\n2\n', b'3\n4\n\n'
    before = before.replace(b'\n', b'\r\n') if crlf_before else before
    after = after.replace(b'\n', b'\r\n') if crlf_after else after

    _write(before)
    cmd_output('git', 'add', 'foo')
    _write(after)
    with staged_files_only(patch_dir):
        assert_no_diff()


def test_whitespace_errors(in_git_dir, patch_dir):
    cmd_output('git', 'config', '--local', 'apply.whitespace', 'error')
    test_crlf(in_git_dir, patch_dir, True, True, 'true')


def test_autocrlf_committed_crlf(in_git_dir, patch_dir):
    """Regression test for #570"""
    cmd_output('git', 'config', '--local', 'core.autocrlf', 'false')
    _write(b'1\r\n2\r\n')
    cmd_output('git', 'add', 'foo')
    git_commit()

    cmd_output('git', 'config', '--local', 'core.autocrlf', 'true')
    _write(b'1\r\n2\r\n\r\n\r\n\r\n')

    with staged_files_only(patch_dir):
        assert_no_diff()


def test_intent_to_add(in_git_dir, patch_dir):
    """Regression test for #881"""
    _write(b'hello\nworld\n')
    cmd_output('git', 'add', '--intent-to-add', 'foo')

    assert git.intent_to_add_files() == ['foo']
    with staged_files_only(patch_dir):
        assert_no_diff()
    assert git.intent_to_add_files() == ['foo']
