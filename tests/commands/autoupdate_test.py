from __future__ import unicode_literals

import os.path
import pipes
import shutil
from collections import OrderedDict

import pytest

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import load_config
from pre_commit.commands.autoupdate import _update_repo
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.autoupdate import RepositoryCannotBeUpdatedError
from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import add_config_to_repo
from testing.fixtures import config_with_local_hooks
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.fixtures import write_config
from testing.util import get_resource_path


@pytest.fixture
def up_to_date_repo(tempdir_factory):
    yield make_repo(tempdir_factory, 'python_hooks_repo')


def test_up_to_date_repo(up_to_date_repo, store):
    config = make_config_from_repo(up_to_date_repo)
    input_rev = config['rev']
    ret = _update_repo(config, store, tags_only=False)
    assert ret['rev'] == input_rev


def test_autoupdate_up_to_date_repo(up_to_date_repo, in_tmpdir, store):
    # Write out the config
    config = make_config_from_repo(up_to_date_repo, check=False)
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    assert '^$' not in before
    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False)
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before == after


def test_autoupdate_old_revision_broken(tempdir_factory, in_tmpdir, store):
    """In $FUTURE_VERSION, hooks.yaml will no longer be supported.  This
    asserts that when that day comes, pre-commit will be able to autoupdate
    despite not being able to read hooks.yaml in that repository.
    """
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path, check=False)

    cmd_output('git', 'mv', C.MANIFEST_FILE, 'nope.yaml', cwd=path)
    cmd_output('git', 'commit', '-m', 'simulate old repo', cwd=path)
    # Assume this is the revision the user's old repository was at
    rev = git.head_rev(path)
    cmd_output('git', 'mv', 'nope.yaml', C.MANIFEST_FILE, cwd=path)
    cmd_output('git', 'commit', '-m', 'move hooks file', cwd=path)
    update_rev = git.head_rev(path)

    config['rev'] = rev
    write_config('.', config)
    with open(C.CONFIG_FILE) as f:
        before = f.read()
    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False)
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before != after
    assert update_rev in after


@pytest.fixture
def out_of_date_repo(tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    original_rev = git.head_rev(path)

    # Make a commit
    cmd_output('git', 'commit', '--allow-empty', '-m', 'foo', cwd=path)
    head_rev = git.head_rev(path)

    yield auto_namedtuple(
        path=path, original_rev=original_rev, head_rev=head_rev,
    )


def test_out_of_date_repo(out_of_date_repo, store):
    config = make_config_from_repo(
        out_of_date_repo.path, rev=out_of_date_repo.original_rev,
    )
    ret = _update_repo(config, store, tags_only=False)
    assert ret['rev'] != out_of_date_repo.original_rev
    assert ret['rev'] == out_of_date_repo.head_rev


def test_autoupdate_out_of_date_repo(out_of_date_repo, in_tmpdir, store):
    # Write out the config
    config = make_config_from_repo(
        out_of_date_repo.path, rev=out_of_date_repo.original_rev, check=False,
    )
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False)
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before != after
    # Make sure we don't add defaults
    assert 'exclude' not in after
    assert out_of_date_repo.head_rev in after


def test_autoupdate_out_of_date_repo_with_correct_repo_name(
        out_of_date_repo, in_tmpdir, store,
):
    stale_config = make_config_from_repo(
        out_of_date_repo.path, rev=out_of_date_repo.original_rev, check=False,
    )
    local_config = config_with_local_hooks()
    config = {'repos': [stale_config, local_config]}
    # Write out the config
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    repo_name = 'file://{}'.format(out_of_date_repo.path)
    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False, repos=(repo_name,))
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before != after
    assert out_of_date_repo.head_rev in after
    assert local_config['repo'] in after


def test_autoupdate_out_of_date_repo_with_wrong_repo_name(
        out_of_date_repo, in_tmpdir, store,
):
    # Write out the config
    config = make_config_from_repo(
        out_of_date_repo.path, rev=out_of_date_repo.original_rev, check=False,
    )
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    # It will not update it, because the name doesn't match
    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False, repos=('dne',))
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before == after


def test_does_not_reformat(in_tmpdir, out_of_date_repo, store):
    fmt = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}  # definitely the version I want!\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        # These args are because reasons!\n'
        '        args: [foo, bar, baz]\n'
    )
    config = fmt.format(out_of_date_repo.path, out_of_date_repo.original_rev)
    with open(C.CONFIG_FILE, 'w') as f:
        f.write(config)

    autoupdate(C.CONFIG_FILE, store, tags_only=False)
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    expected = fmt.format(out_of_date_repo.path, out_of_date_repo.head_rev)
    assert after == expected


def test_loses_formatting_when_not_detectable(
        out_of_date_repo, store, in_tmpdir,
):
    """A best-effort attempt is made at updating rev without rewriting
    formatting.  When the original formatting cannot be detected, this
    is abandoned.
    """
    config = (
        'repos: [\n'
        '    {{\n'
        '        repo: {}, rev: {},\n'
        '        hooks: [\n'
        '            # A comment!\n'
        '            {{id: foo}},\n'
        '        ],\n'
        '    }}\n'
        ']\n'.format(
            pipes.quote(out_of_date_repo.path), out_of_date_repo.original_rev,
        )
    )
    with open(C.CONFIG_FILE, 'w') as f:
        f.write(config)

    autoupdate(C.CONFIG_FILE, store, tags_only=False)
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    expected = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    ).format(out_of_date_repo.path, out_of_date_repo.head_rev)
    assert after == expected


@pytest.fixture
def tagged_repo(out_of_date_repo):
    cmd_output('git', 'tag', 'v1.2.3', cwd=out_of_date_repo.path)
    yield out_of_date_repo


def test_autoupdate_tagged_repo(tagged_repo, in_tmpdir, store):
    config = make_config_from_repo(
        tagged_repo.path, rev=tagged_repo.original_rev,
    )
    write_config('.', config)

    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False)
    assert ret == 0
    with open(C.CONFIG_FILE) as f:
        assert 'v1.2.3' in f.read()


@pytest.fixture
def tagged_repo_with_more_commits(tagged_repo):
    cmd_output('git', 'commit', '--allow-empty', '-mfoo', cwd=tagged_repo.path)
    yield tagged_repo


def test_autoupdate_tags_only(tagged_repo_with_more_commits, in_tmpdir, store):
    config = make_config_from_repo(
        tagged_repo_with_more_commits.path,
        rev=tagged_repo_with_more_commits.original_rev,
    )
    write_config('.', config)

    ret = autoupdate(C.CONFIG_FILE, store, tags_only=True)
    assert ret == 0
    with open(C.CONFIG_FILE) as f:
        assert 'v1.2.3' in f.read()


def test_autoupdate_latest_no_config(out_of_date_repo, in_tmpdir, store):
    config = make_config_from_repo(
        out_of_date_repo.path, rev=out_of_date_repo.original_rev,
    )
    write_config('.', config)

    cmd_output('git', '-C', out_of_date_repo.path, 'rm', '-r', ':/')
    cmd_output('git', '-C', out_of_date_repo.path, 'commit', '-m', 'rm')

    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False)
    assert ret == 1
    with open(C.CONFIG_FILE) as f:
        assert out_of_date_repo.original_rev in f.read()


@pytest.fixture
def hook_disappearing_repo(tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    original_rev = git.head_rev(path)

    shutil.copy(
        get_resource_path('manifest_without_foo.yaml'),
        os.path.join(path, C.MANIFEST_FILE),
    )
    cmd_output('git', 'add', '.', cwd=path)
    cmd_output('git', 'commit', '-m', 'Remove foo', cwd=path)

    yield auto_namedtuple(path=path, original_rev=original_rev)


def test_hook_disppearing_repo_raises(hook_disappearing_repo, store):
    config = make_config_from_repo(
        hook_disappearing_repo.path,
        rev=hook_disappearing_repo.original_rev,
        hooks=[OrderedDict((('id', 'foo'),))],
    )
    with pytest.raises(RepositoryCannotBeUpdatedError):
        _update_repo(config, store, tags_only=False)


def test_autoupdate_hook_disappearing_repo(
        hook_disappearing_repo, in_tmpdir, store,
):
    config = make_config_from_repo(
        hook_disappearing_repo.path,
        rev=hook_disappearing_repo.original_rev,
        hooks=[OrderedDict((('id', 'foo'),))],
        check=False,
    )
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    ret = autoupdate(C.CONFIG_FILE, store, tags_only=False)
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 1
    assert before == after


def test_autoupdate_local_hooks(in_git_dir, store):
    config = config_with_local_hooks()
    add_config_to_repo('.', config)
    assert autoupdate(C.CONFIG_FILE, store, tags_only=False) == 0
    new_config_writen = load_config(C.CONFIG_FILE)
    assert len(new_config_writen['repos']) == 1
    assert new_config_writen['repos'][0] == config


def test_autoupdate_local_hooks_with_out_of_date_repo(
        out_of_date_repo, in_tmpdir, store,
):
    stale_config = make_config_from_repo(
        out_of_date_repo.path, rev=out_of_date_repo.original_rev, check=False,
    )
    local_config = config_with_local_hooks()
    config = {'repos': [local_config, stale_config]}
    write_config('.', config)
    assert autoupdate(C.CONFIG_FILE, store, tags_only=False) == 0
    new_config_writen = load_config(C.CONFIG_FILE)
    assert len(new_config_writen['repos']) == 2
    assert new_config_writen['repos'][0] == local_config


def test_autoupdate_meta_hooks(tmpdir, capsys, store):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        'repos:\n'
        '-   repo: meta\n'
        '    hooks:\n'
        '    -   id: check-useless-excludes\n',
    )
    with tmpdir.as_cwd():
        ret = autoupdate(C.CONFIG_FILE, store, tags_only=True)
    assert ret == 0
    assert cfg.read() == (
        'repos:\n'
        '-   repo: meta\n'
        '    hooks:\n'
        '    -   id: check-useless-excludes\n'
    )


def test_updates_old_format_to_new_format(tmpdir, capsys, store):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n',
    )
    with tmpdir.as_cwd():
        ret = autoupdate(C.CONFIG_FILE, store, tags_only=True)
    assert ret == 0
    contents = cfg.read()
    assert contents == (
        'repos:\n'
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n'
    )
    out, _ = capsys.readouterr()
    assert out == 'Configuration has been migrated.\n'
