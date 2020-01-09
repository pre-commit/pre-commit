import pipes

import pytest

import pre_commit.constants as C
from pre_commit import git
from pre_commit.commands.autoupdate import _check_hooks_still_exist_at_rev
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.autoupdate import RepositoryCannotBeUpdatedError
from pre_commit.commands.autoupdate import RevInfo
from pre_commit.util import cmd_output
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import add_config_to_repo
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.fixtures import modify_manifest
from testing.fixtures import read_config
from testing.fixtures import sample_local_config
from testing.fixtures import write_config
from testing.util import git_commit


@pytest.fixture
def up_to_date(tempdir_factory):
    yield make_repo(tempdir_factory, 'python_hooks_repo')


@pytest.fixture
def out_of_date(tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    original_rev = git.head_rev(path)

    git_commit(cwd=path)
    head_rev = git.head_rev(path)

    yield auto_namedtuple(
        path=path, original_rev=original_rev, head_rev=head_rev,
    )


@pytest.fixture
def tagged(out_of_date):
    cmd_output('git', 'tag', 'v1.2.3', cwd=out_of_date.path)
    yield out_of_date


@pytest.fixture
def hook_disappearing(tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    original_rev = git.head_rev(path)

    with modify_manifest(path) as manifest:
        manifest[0]['id'] = 'bar'

    yield auto_namedtuple(path=path, original_rev=original_rev)


def test_rev_info_from_config():
    info = RevInfo.from_config({'repo': 'repo/path', 'rev': 'v1.2.3'})
    assert info == RevInfo('repo/path', 'v1.2.3', None)


def test_rev_info_update_up_to_date_repo(up_to_date):
    config = make_config_from_repo(up_to_date)
    info = RevInfo.from_config(config)
    new_info = info.update(tags_only=False, freeze=False)
    assert info == new_info


def test_rev_info_update_out_of_date_repo(out_of_date):
    config = make_config_from_repo(
        out_of_date.path, rev=out_of_date.original_rev,
    )
    info = RevInfo.from_config(config)
    new_info = info.update(tags_only=False, freeze=False)
    assert new_info.rev == out_of_date.head_rev


def test_rev_info_update_non_master_default_branch(out_of_date):
    # change the default branch to be not-master
    cmd_output('git', '-C', out_of_date.path, 'branch', '-m', 'dev')
    test_rev_info_update_out_of_date_repo(out_of_date)


def test_rev_info_update_tags_even_if_not_tags_only(tagged):
    config = make_config_from_repo(tagged.path, rev=tagged.original_rev)
    info = RevInfo.from_config(config)
    new_info = info.update(tags_only=False, freeze=False)
    assert new_info.rev == 'v1.2.3'


def test_rev_info_update_tags_only_does_not_pick_tip(tagged):
    git_commit(cwd=tagged.path)
    config = make_config_from_repo(tagged.path, rev=tagged.original_rev)
    info = RevInfo.from_config(config)
    new_info = info.update(tags_only=True, freeze=False)
    assert new_info.rev == 'v1.2.3'


def test_rev_info_update_freeze_tag(tagged):
    git_commit(cwd=tagged.path)
    config = make_config_from_repo(tagged.path, rev=tagged.original_rev)
    info = RevInfo.from_config(config)
    new_info = info.update(tags_only=True, freeze=True)
    assert new_info.rev == tagged.head_rev
    assert new_info.frozen == 'v1.2.3'


def test_rev_info_update_does_not_freeze_if_already_sha(out_of_date):
    config = make_config_from_repo(
        out_of_date.path, rev=out_of_date.original_rev,
    )
    info = RevInfo.from_config(config)
    new_info = info.update(tags_only=True, freeze=True)
    assert new_info.rev == out_of_date.head_rev
    assert new_info.frozen is None


def test_autoupdate_up_to_date_repo(up_to_date, tmpdir, store):
    contents = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    ).format(up_to_date, git.head_rev(up_to_date))
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(contents)

    assert autoupdate(str(cfg), store, freeze=False, tags_only=False) == 0
    assert cfg.read() == contents


def test_autoupdate_old_revision_broken(tempdir_factory, in_tmpdir, store):
    """In $FUTURE_VERSION, hooks.yaml will no longer be supported.  This
    asserts that when that day comes, pre-commit will be able to autoupdate
    despite not being able to read hooks.yaml in that repository.
    """
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    config = make_config_from_repo(path, check=False)

    cmd_output('git', 'mv', C.MANIFEST_FILE, 'nope.yaml', cwd=path)
    git_commit(cwd=path)
    # Assume this is the revision the user's old repository was at
    rev = git.head_rev(path)
    cmd_output('git', 'mv', 'nope.yaml', C.MANIFEST_FILE, cwd=path)
    git_commit(cwd=path)
    update_rev = git.head_rev(path)

    config['rev'] = rev
    write_config('.', config)
    with open(C.CONFIG_FILE) as f:
        before = f.read()
    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False) == 0
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert before != after
    assert update_rev in after


def test_autoupdate_out_of_date_repo(out_of_date, tmpdir, store):
    fmt = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    )
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(fmt.format(out_of_date.path, out_of_date.original_rev))

    assert autoupdate(str(cfg), store, freeze=False, tags_only=False) == 0
    assert cfg.read() == fmt.format(out_of_date.path, out_of_date.head_rev)


def test_autoupdate_only_one_to_update(up_to_date, out_of_date, tmpdir, store):
    fmt = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    )
    cfg = tmpdir.join(C.CONFIG_FILE)
    before = fmt.format(
        up_to_date, git.head_rev(up_to_date),
        out_of_date.path, out_of_date.original_rev,
    )
    cfg.write(before)

    assert autoupdate(str(cfg), store, freeze=False, tags_only=False) == 0
    assert cfg.read() == fmt.format(
        up_to_date, git.head_rev(up_to_date),
        out_of_date.path, out_of_date.head_rev,
    )


def test_autoupdate_out_of_date_repo_with_correct_repo_name(
        out_of_date, in_tmpdir, store,
):
    stale_config = make_config_from_repo(
        out_of_date.path, rev=out_of_date.original_rev, check=False,
    )
    local_config = sample_local_config()
    config = {'repos': [stale_config, local_config]}
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    repo_name = f'file://{out_of_date.path}'
    ret = autoupdate(
        C.CONFIG_FILE, store, freeze=False, tags_only=False,
        repos=(repo_name,),
    )
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before != after
    assert out_of_date.head_rev in after
    assert 'local' in after


def test_autoupdate_out_of_date_repo_with_wrong_repo_name(
        out_of_date, in_tmpdir, store,
):
    config = make_config_from_repo(
        out_of_date.path, rev=out_of_date.original_rev, check=False,
    )
    write_config('.', config)

    with open(C.CONFIG_FILE) as f:
        before = f.read()
    # It will not update it, because the name doesn't match
    ret = autoupdate(
        C.CONFIG_FILE, store, freeze=False, tags_only=False,
        repos=('dne',),
    )
    with open(C.CONFIG_FILE) as f:
        after = f.read()
    assert ret == 0
    assert before == after


def test_does_not_reformat(tmpdir, out_of_date, store):
    fmt = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}  # definitely the version I want!\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        # These args are because reasons!\n'
        '        args: [foo, bar, baz]\n'
    )
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(fmt.format(out_of_date.path, out_of_date.original_rev))

    assert autoupdate(str(cfg), store, freeze=False, tags_only=False) == 0
    expected = fmt.format(out_of_date.path, out_of_date.head_rev)
    assert cfg.read() == expected


def test_loses_formatting_when_not_detectable(out_of_date, store, tmpdir):
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
            pipes.quote(out_of_date.path), out_of_date.original_rev,
        )
    )
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(config)

    assert autoupdate(str(cfg), store, freeze=False, tags_only=False) == 0
    expected = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    ).format(out_of_date.path, out_of_date.head_rev)
    assert cfg.read() == expected


def test_autoupdate_tagged_repo(tagged, in_tmpdir, store):
    config = make_config_from_repo(tagged.path, rev=tagged.original_rev)
    write_config('.', config)

    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False) == 0
    with open(C.CONFIG_FILE) as f:
        assert 'v1.2.3' in f.read()


def test_autoupdate_freeze(tagged, in_tmpdir, store):
    config = make_config_from_repo(tagged.path, rev=tagged.original_rev)
    write_config('.', config)

    assert autoupdate(C.CONFIG_FILE, store, freeze=True, tags_only=False) == 0
    with open(C.CONFIG_FILE) as f:
        expected = f'rev: {tagged.head_rev}  # frozen: v1.2.3'
        assert expected in f.read()

    # if we un-freeze it should remove the frozen comment
    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False) == 0
    with open(C.CONFIG_FILE) as f:
        assert 'rev: v1.2.3\n' in f.read()


def test_autoupdate_tags_only(tagged, in_tmpdir, store):
    # add some commits after the tag
    git_commit(cwd=tagged.path)

    config = make_config_from_repo(tagged.path, rev=tagged.original_rev)
    write_config('.', config)

    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=True) == 0
    with open(C.CONFIG_FILE) as f:
        assert 'v1.2.3' in f.read()


def test_autoupdate_latest_no_config(out_of_date, in_tmpdir, store):
    config = make_config_from_repo(
        out_of_date.path, rev=out_of_date.original_rev,
    )
    write_config('.', config)

    cmd_output('git', 'rm', '-r', ':/', cwd=out_of_date.path)
    git_commit(cwd=out_of_date.path)

    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False) == 1
    with open(C.CONFIG_FILE) as f:
        assert out_of_date.original_rev in f.read()


def test_hook_disppearing_repo_raises(hook_disappearing, store):
    config = make_config_from_repo(
        hook_disappearing.path,
        rev=hook_disappearing.original_rev,
        hooks=[{'id': 'foo'}],
    )
    info = RevInfo.from_config(config).update(tags_only=False, freeze=False)
    with pytest.raises(RepositoryCannotBeUpdatedError):
        _check_hooks_still_exist_at_rev(config, info, store)


def test_autoupdate_hook_disappearing_repo(hook_disappearing, tmpdir, store):
    contents = (
        'repos:\n'
        '-   repo: {}\n'
        '    rev: {}\n'
        '    hooks:\n'
        '    -   id: foo\n'
    ).format(hook_disappearing.path, hook_disappearing.original_rev)
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(contents)

    assert autoupdate(str(cfg), store, freeze=False, tags_only=False) == 1
    assert cfg.read() == contents


def test_autoupdate_local_hooks(in_git_dir, store):
    config = sample_local_config()
    add_config_to_repo('.', config)
    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False) == 0
    new_config_writen = read_config('.')
    assert len(new_config_writen['repos']) == 1
    assert new_config_writen['repos'][0] == config


def test_autoupdate_local_hooks_with_out_of_date_repo(
        out_of_date, in_tmpdir, store,
):
    stale_config = make_config_from_repo(
        out_of_date.path, rev=out_of_date.original_rev, check=False,
    )
    local_config = sample_local_config()
    config = {'repos': [local_config, stale_config]}
    write_config('.', config)
    assert autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False) == 0
    new_config_writen = read_config('.')
    assert len(new_config_writen['repos']) == 2
    assert new_config_writen['repos'][0] == local_config


def test_autoupdate_meta_hooks(tmpdir, store):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        'repos:\n'
        '-   repo: meta\n'
        '    hooks:\n'
        '    -   id: check-useless-excludes\n',
    )
    assert autoupdate(str(cfg), store, freeze=False, tags_only=True) == 0
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
    assert autoupdate(str(cfg), store, freeze=False, tags_only=True) == 0
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
