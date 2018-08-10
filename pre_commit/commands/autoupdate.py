from __future__ import print_function
from __future__ import unicode_literals

import re
from collections import OrderedDict

from aspy.yaml import ordered_dump
from aspy.yaml import ordered_load
from cfgv import remove_defaults

import pre_commit.constants as C
from pre_commit import output
from pre_commit.clientlib import CONFIG_SCHEMA
from pre_commit.clientlib import is_local_repo
from pre_commit.clientlib import is_meta_repo
from pre_commit.clientlib import load_config
from pre_commit.commands.migrate_config import migrate_config
from pre_commit.repository import Repository
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output


class RepositoryCannotBeUpdatedError(RuntimeError):
    pass


def _update_repo(repo_config, store, tags_only):
    """Updates a repository to the tip of `master`.  If the repository cannot
    be updated because a hook that is configured does not exist in `master`,
    this raises a RepositoryCannotBeUpdatedError

    Args:
        repo_config - A config for a repository
    """
    repo_path = store.clone(repo_config['repo'], repo_config['rev'])

    cmd_output('git', 'fetch', cwd=repo_path)
    tag_cmd = ('git', 'describe', 'origin/master', '--tags')
    if tags_only:
        tag_cmd += ('--abbrev=0',)
    else:
        tag_cmd += ('--exact',)
    try:
        rev = cmd_output(*tag_cmd, cwd=repo_path)[1].strip()
    except CalledProcessError:
        tag_cmd = ('git', 'rev-parse', 'origin/master')
        rev = cmd_output(*tag_cmd, cwd=repo_path)[1].strip()

    # Don't bother trying to update if our rev is the same
    if rev == repo_config['rev']:
        return repo_config

    # Construct a new config with the head rev
    new_config = OrderedDict(repo_config)
    new_config['rev'] = rev
    new_repo = Repository.create(new_config, store)

    # See if any of our hooks were deleted with the new commits
    hooks = {hook['id'] for hook in repo_config['hooks']}
    hooks_missing = hooks - (hooks & set(new_repo.manifest_hooks))
    if hooks_missing:
        raise RepositoryCannotBeUpdatedError(
            'Cannot update because the tip of master is missing these hooks:\n'
            '{}'.format(', '.join(sorted(hooks_missing))),
        )

    return new_config


REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([^\s#]+)(.*)$', re.DOTALL)
REV_LINE_FMT = '{}rev:{}{}{}'


def _write_new_config_file(path, output):
    with open(path) as f:
        original_contents = f.read()
    output = remove_defaults(output, CONFIG_SCHEMA)
    new_contents = ordered_dump(output, **C.YAML_DUMP_KWARGS)

    lines = original_contents.splitlines(True)
    rev_line_indices_reversed = list(reversed([
        i for i, line in enumerate(lines) if REV_LINE_RE.match(line)
    ]))

    for line in new_contents.splitlines(True):
        if REV_LINE_RE.match(line):
            # It's possible we didn't identify the rev lines in the original
            if not rev_line_indices_reversed:
                break
            line_index = rev_line_indices_reversed.pop()
            original_line = lines[line_index]
            orig_match = REV_LINE_RE.match(original_line)
            new_match = REV_LINE_RE.match(line)
            lines[line_index] = REV_LINE_FMT.format(
                orig_match.group(1), orig_match.group(2),
                new_match.group(3), orig_match.group(4),
            )

    # If we failed to intelligently rewrite the rev lines, fall back to the
    # pretty-formatted yaml output
    to_write = ''.join(lines)
    if remove_defaults(ordered_load(to_write), CONFIG_SCHEMA) != output:
        to_write = new_contents

    with open(path, 'w') as f:
        f.write(to_write)


def autoupdate(runner, store, tags_only, repos=()):
    """Auto-update the pre-commit config to the latest versions of repos."""
    migrate_config(runner, quiet=True)
    retv = 0
    output_repos = []
    changed = False

    input_config = load_config(runner.config_file_path)

    for repo_config in input_config['repos']:
        if (
            is_local_repo(repo_config) or
            is_meta_repo(repo_config) or
            # Skip updating any repo_configs that aren't for the specified repo
            repos and repo_config['repo'] not in repos
        ):
            output_repos.append(repo_config)
            continue
        output.write('Updating {}...'.format(repo_config['repo']))
        try:
            new_repo_config = _update_repo(repo_config, store, tags_only)
        except RepositoryCannotBeUpdatedError as error:
            output.write_line(error.args[0])
            output_repos.append(repo_config)
            retv = 1
            continue

        if new_repo_config['rev'] != repo_config['rev']:
            changed = True
            output.write_line('updating {} -> {}.'.format(
                repo_config['rev'], new_repo_config['rev'],
            ))
            output_repos.append(new_repo_config)
        else:
            output.write_line('already up to date.')
            output_repos.append(repo_config)

    if changed:
        output_config = input_config.copy()
        output_config['repos'] = output_repos
        _write_new_config_file(runner.config_file_path, output_config)

    return retv
