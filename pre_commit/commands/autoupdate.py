from __future__ import print_function
from __future__ import unicode_literals

import collections
import os.path
import re

import six
from aspy.yaml import ordered_dump
from aspy.yaml import ordered_load

import pre_commit.constants as C
from pre_commit import git
from pre_commit import output
from pre_commit.clientlib import InvalidManifestError
from pre_commit.clientlib import load_config
from pre_commit.clientlib import load_manifest
from pre_commit.clientlib import LOCAL
from pre_commit.clientlib import META
from pre_commit.commands.migrate_config import migrate_config
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b
from pre_commit.util import tmpdir


class RevInfo(collections.namedtuple('RevInfo', ('repo', 'rev', 'frozen'))):
    __slots__ = ()

    @classmethod
    def from_config(cls, config):
        return cls(config['repo'], config['rev'], None)

    def update(self, tags_only, freeze):
        if tags_only:
            tag_cmd = ('git', 'describe', 'FETCH_HEAD', '--tags', '--abbrev=0')
        else:
            tag_cmd = ('git', 'describe', 'FETCH_HEAD', '--tags', '--exact')

        with tmpdir() as tmp:
            git.init_repo(tmp, self.repo)
            cmd_output_b('git', 'fetch', 'origin', 'HEAD', '--tags', cwd=tmp)

            try:
                rev = cmd_output(*tag_cmd, cwd=tmp)[1].strip()
            except CalledProcessError:
                cmd = ('git', 'rev-parse', 'FETCH_HEAD')
                rev = cmd_output(*cmd, cwd=tmp)[1].strip()

            frozen = None
            if freeze:
                exact = cmd_output('git', 'rev-parse', rev, cwd=tmp)[1].strip()
                if exact != rev:
                    rev, frozen = exact, rev
        return self._replace(rev=rev, frozen=frozen)


class RepositoryCannotBeUpdatedError(RuntimeError):
    pass


def _check_hooks_still_exist_at_rev(repo_config, info, store):
    try:
        path = store.clone(repo_config['repo'], info.rev)
        manifest = load_manifest(os.path.join(path, C.MANIFEST_FILE))
    except InvalidManifestError as e:
        raise RepositoryCannotBeUpdatedError(six.text_type(e))

    # See if any of our hooks were deleted with the new commits
    hooks = {hook['id'] for hook in repo_config['hooks']}
    hooks_missing = hooks - {hook['id'] for hook in manifest}
    if hooks_missing:
        raise RepositoryCannotBeUpdatedError(
            'Cannot update because the tip of master is missing these hooks:\n'
            '{}'.format(', '.join(sorted(hooks_missing))),
        )


REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([^\s#]+)(.*)(\r?\n)$', re.DOTALL)
REV_LINE_FMT = '{}rev:{}{}{}{}'


def _original_lines(path, rev_infos, retry=False):
    """detect `rev:` lines or reformat the file"""
    with open(path) as f:
        original = f.read()

    lines = original.splitlines(True)
    idxs = [i for i, line in enumerate(lines) if REV_LINE_RE.match(line)]
    if len(idxs) == len(rev_infos):
        return lines, idxs
    elif retry:
        raise AssertionError('could not find rev lines')
    else:
        with open(path, 'w') as f:
            f.write(ordered_dump(ordered_load(original), **C.YAML_DUMP_KWARGS))
        return _original_lines(path, rev_infos, retry=True)


def _write_new_config(path, rev_infos):
    lines, idxs = _original_lines(path, rev_infos)

    for idx, rev_info in zip(idxs, rev_infos):
        if rev_info is None:
            continue
        match = REV_LINE_RE.match(lines[idx])
        assert match is not None
        new_rev_s = ordered_dump({'rev': rev_info.rev}, **C.YAML_DUMP_KWARGS)
        new_rev = new_rev_s.split(':', 1)[1].strip()
        if rev_info.frozen is not None:
            comment = '  # frozen: {}'.format(rev_info.frozen)
        elif match.group(4).strip().startswith('# frozen:'):
            comment = ''
        else:
            comment = match.group(4)
        lines[idx] = REV_LINE_FMT.format(
            match.group(1), match.group(2), new_rev, comment, match.group(5),
        )

    with open(path, 'w') as f:
        f.write(''.join(lines))


def autoupdate(config_file, store, tags_only, freeze, repos=()):
    """Auto-update the pre-commit config to the latest versions of repos."""
    migrate_config(config_file, quiet=True)
    retv = 0
    rev_infos = []
    changed = False

    config = load_config(config_file)
    for repo_config in config['repos']:
        if repo_config['repo'] in {LOCAL, META}:
            continue

        info = RevInfo.from_config(repo_config)
        if repos and info.repo not in repos:
            rev_infos.append(None)
            continue

        output.write('Updating {} ... '.format(info.repo))
        new_info = info.update(tags_only=tags_only, freeze=freeze)
        try:
            _check_hooks_still_exist_at_rev(repo_config, new_info, store)
        except RepositoryCannotBeUpdatedError as error:
            output.write_line(error.args[0])
            rev_infos.append(None)
            retv = 1
            continue

        if new_info.rev != info.rev:
            changed = True
            if new_info.frozen:
                updated_to = '{} (frozen)'.format(new_info.frozen)
            else:
                updated_to = new_info.rev
            msg = 'updating {} -> {}.'.format(info.rev, updated_to)
            output.write_line(msg)
            rev_infos.append(new_info)
        else:
            output.write_line('already up to date.')
            rev_infos.append(None)

    if changed:
        _write_new_config(config_file, rev_infos)

    return retv
