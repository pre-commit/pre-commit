from __future__ import unicode_literals

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
from pre_commit.runner import Runner
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import add_config_to_repo
from testing.fixtures import config_with_local_hooks
from testing.fixtures import git_dir
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.fixtures import write_config
from testing.util import get_resource_path


@pytest.yield_fixture
def up_to_date_repo(tempdir_factory):
    yield make_repo(tempdir_factory, 'python_hooks_repo')


def test_up_to_date_repo(up_to_date_repo, runner_with_mocked_store):
    config = make_config_from_repo(up_to_date_repo)
    input_sha = config['sha']
    ret = _update_repo(config, runner_with_mocked_store, tags_only=False)
    assert ret['sha'] == input_sha


def test_autoupdate_up_to_date_repo(
        up_to_date_repo, in_tmpdir, mock_out_store_directory,
):
    # Write out the config
    config = make_config_from_repo(up_to_date_repo, check=False)
    write_config('.', config)

    before = open(C.CONFIG_FILE).read()
    assert '^$' not in before
    ret = autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before == after


def test_autoupdate_old_revision_broken(
    tempdir_factory, in_tmpdir, mock_out_store_directory,
):
    """In $FUTURE_VERSION, hooks.yaml will no longer be supported.  This
    asserts that when that day comes, pre-commit will be able to autoupdate
    despite not being able to read hooks.yaml in that repository.
    """
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path, check=False)

    with cwd(path):
        cmd_output('git', 'mv', C.MANIFEST_FILE, 'nope.yaml')
        cmd_output('git', 'commit', '-m', 'simulate old repo')
        # Assume this is the revision the user's old repository was at
        rev = git.head_sha(path)
        cmd_output('git', 'mv', 'nope.yaml', C.MANIFEST_FILE)
        cmd_output('git', 'commit', '-m', 'move hooks file')
        update_rev = git.head_sha(path)

    config['sha'] = rev
    write_config('.', config)
    before = open(C.CONFIG_FILE).read()
    ret = autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before != after
    assert update_rev in after


@pytest.yield_fixture
def out_of_date_repo(tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    original_sha = git.head_sha(path)

    # Make a commit
    with cwd(path):
        cmd_output('git', 'commit', '--allow-empty', '-m', 'foo')
    head_sha = git.head_sha(path)

    yield auto_namedtuple(
        path=path, original_sha=original_sha, head_sha=head_sha,
    )


def test_out_of_date_repo(out_of_date_repo, runner_with_mocked_store):
    config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha,
    )
    ret = _update_repo(config, runner_with_mocked_store, tags_only=False)
    assert ret['sha'] != out_of_date_repo.original_sha
    assert ret['sha'] == out_of_date_repo.head_sha


def test_autoupdate_out_of_date_repo(
        out_of_date_repo, in_tmpdir, mock_out_store_directory,
):
    # Write out the config
    config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha, check=False,
    )
    write_config('.', config)

    before = open(C.CONFIG_FILE).read()
    ret = autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before != after
    # Make sure we don't add defaults
    assert 'exclude' not in after
    assert out_of_date_repo.head_sha in after

def test_autoupdate_out_of_date_repo_with_correct_repo_name(
        out_of_date_repo, in_tmpdir, mock_out_store_directory,
):
    # Write out the config
    config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha, check=False,
    )
    write_config('.', config)

    runner = Runner('.', C.CONFIG_FILE)
    before = open(C.CONFIG_FILE).read()
    repo_name = 'file://{}'.format(out_of_date_repo.path)
    ret = autoupdate(runner, tags_only=False, repo=repo_name)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before != after
    # Make sure we don't add defaults
    assert 'exclude' not in after
    assert out_of_date_repo.head_sha in after

def test_autoupdate_out_of_date_repo_with_wrong_repo_name(
        out_of_date_repo, in_tmpdir, mock_out_store_directory,
):
    # Write out the config
    config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha, check=False,
    )
    write_config('.', config)

    runner = Runner('.', C.CONFIG_FILE)
    before = open(C.CONFIG_FILE).read()
    # It will not update it, because the name doesn't match
    ret = autoupdate(runner, tags_only=False, repo='wrong_repo_name')
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before == after

def test_does_not_reformat(
        out_of_date_repo, mock_out_store_directory, in_tmpdir,
):
    fmt = (
        'repos:\n'
        '-   repo: {}\n'
        '    sha: {}  # definitely the version I want!\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        # These args are because reasons!\n'
        '        args: [foo, bar, baz]\n'
    )
    config = fmt.format(out_of_date_repo.path, out_of_date_repo.original_sha)
    with open(C.CONFIG_FILE, 'w') as f:
        f.write(config)

    autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    after = open(C.CONFIG_FILE).read()
    expected = fmt.format(out_of_date_repo.path, out_of_date_repo.head_sha)
    assert after == expected


def test_loses_formatting_when_not_detectable(
        out_of_date_repo, mock_out_store_directory, in_tmpdir,
):
    """A best-effort attempt is made at updating sha without rewriting
    formatting.  When the original formatting cannot be detected, this
    is abandoned.
    """
    config = (
        'repos: [\n'
        '    {{\n'
        '        repo: {}, sha: {},\n'
        '        hooks: [\n'
        '            # A comment!\n'
        '            {{id: foo}},\n'
        '        ],\n'
        '    }}\n'
        ']\n'.format(
            pipes.quote(out_of_date_repo.path), out_of_date_repo.original_sha,
        )
    )
    with open(C.CONFIG_FILE, 'w') as f:
        f.write(config)

    autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    after = open(C.CONFIG_FILE).read()
    expected = (
        'repos:\n'
        '-   repo: {}\n'
        '    sha: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    ).format(out_of_date_repo.path, out_of_date_repo.head_sha)
    assert after == expected


@pytest.yield_fixture
def tagged_repo(out_of_date_repo):
    with cwd(out_of_date_repo.path):
        cmd_output('git', 'tag', 'v1.2.3')
    yield out_of_date_repo


def test_autoupdate_tagged_repo(
        tagged_repo, in_tmpdir, mock_out_store_directory,
):
    config = make_config_from_repo(
        tagged_repo.path, sha=tagged_repo.original_sha,
    )
    write_config('.', config)

    ret = autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    assert ret == 0
    assert 'v1.2.3' in open(C.CONFIG_FILE).read()


@pytest.yield_fixture
def tagged_repo_with_more_commits(tagged_repo):
    with cwd(tagged_repo.path):
        cmd_output('git', 'commit', '--allow-empty', '-m', 'commit!')
    yield tagged_repo


def test_autoupdate_tags_only(
        tagged_repo_with_more_commits, in_tmpdir, mock_out_store_directory,
):
    config = make_config_from_repo(
        tagged_repo_with_more_commits.path,
        sha=tagged_repo_with_more_commits.original_sha,
    )
    write_config('.', config)

    ret = autoupdate(Runner('.', C.CONFIG_FILE), tags_only=True)
    assert ret == 0
    assert 'v1.2.3' in open(C.CONFIG_FILE).read()


@pytest.yield_fixture
def hook_disappearing_repo(tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    original_sha = git.head_sha(path)

    with cwd(path):
        shutil.copy(
            get_resource_path('manifest_without_foo.yaml'),
            C.MANIFEST_FILE,
        )
        cmd_output('git', 'add', '.')
        cmd_output('git', 'commit', '-m', 'Remove foo')

    yield auto_namedtuple(path=path, original_sha=original_sha)


def test_hook_disppearing_repo_raises(
        hook_disappearing_repo, runner_with_mocked_store,
):
    config = make_config_from_repo(
        hook_disappearing_repo.path,
        sha=hook_disappearing_repo.original_sha,
        hooks=[OrderedDict((('id', 'foo'),))],
    )
    with pytest.raises(RepositoryCannotBeUpdatedError):
        _update_repo(config, runner_with_mocked_store, tags_only=False)


def test_autoupdate_hook_disappearing_repo(
        hook_disappearing_repo, in_tmpdir, mock_out_store_directory,
):
    config = make_config_from_repo(
        hook_disappearing_repo.path,
        sha=hook_disappearing_repo.original_sha,
        hooks=[OrderedDict((('id', 'foo'),))],
        check=False,
    )
    write_config('.', config)

    before = open(C.CONFIG_FILE).read()
    ret = autoupdate(Runner('.', C.CONFIG_FILE), tags_only=False)
    after = open(C.CONFIG_FILE).read()
    assert ret == 1
    assert before == after


def test_autoupdate_local_hooks(tempdir_factory):
    git_path = git_dir(tempdir_factory)
    config = config_with_local_hooks()
    path = add_config_to_repo(git_path, config)
    runner = Runner(path, C.CONFIG_FILE)
    assert autoupdate(runner, tags_only=False) == 0
    new_config_writen = load_config(runner.config_file_path)
    assert len(new_config_writen['repos']) == 1
    assert new_config_writen['repos'][0] == config


def test_autoupdate_local_hooks_with_out_of_date_repo(
        out_of_date_repo, in_tmpdir, mock_out_store_directory,
):
    stale_config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha, check=False,
    )
    local_config = config_with_local_hooks()
    config = {'repos': [local_config, stale_config]}
    write_config('.', config)
    runner = Runner('.', C.CONFIG_FILE)
    assert autoupdate(runner, tags_only=False) == 0
    new_config_writen = load_config(runner.config_file_path)
    assert len(new_config_writen['repos']) == 2
    assert new_config_writen['repos'][0] == local_config


def test_autoupdate_meta_hooks(tmpdir, capsys):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        'repos:\n'
        '-   repo: meta\n'
        '    hooks:\n'
        '    -   id: check-useless-excludes\n',
    )
    ret = autoupdate(Runner(tmpdir.strpath, C.CONFIG_FILE), tags_only=True)
    assert ret == 0
    assert cfg.read() == (
        'repos:\n'
        '-   repo: meta\n'
        '    hooks:\n'
        '    -   id: check-useless-excludes\n'
    )


def test_updates_old_format_to_new_format(tmpdir, capsys):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n',
    )
    ret = autoupdate(Runner(tmpdir.strpath, C.CONFIG_FILE), tags_only=True)
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
