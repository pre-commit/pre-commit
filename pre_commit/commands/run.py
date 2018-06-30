from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import re
import subprocess
import sys

from identify.identify import tags_from_path

from pre_commit import color
from pre_commit import git
from pre_commit import output
from pre_commit.output import get_hook_message
from pre_commit.repository import repositories
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import cmd_output
from pre_commit.util import memoize_by_cwd
from pre_commit.util import noop_context


logger = logging.getLogger('pre_commit')


tags_from_path = memoize_by_cwd(tags_from_path)


def _get_skips(environ):
    skips = environ.get('SKIP', '')
    return {skip.strip() for skip in skips.split(',') if skip.strip()}


def _hook_msg_start(hook, verbose):
    return '{}{}'.format(
        '[{}] '.format(hook['id']) if verbose else '', hook['name'],
    )


def _filter_by_include_exclude(filenames, include, exclude):
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    return [
        filename for filename in filenames
        if (
            include_re.search(filename) and
            not exclude_re.search(filename) and
            os.path.lexists(filename)
        )
    ]


def _filter_by_types(filenames, types, exclude_types):
    types, exclude_types = frozenset(types), frozenset(exclude_types)
    ret = []
    for filename in filenames:
        tags = tags_from_path(filename)
        if tags >= types and not tags & exclude_types:
            ret.append(filename)
    return tuple(ret)


SKIPPED = 'Skipped'
NO_FILES = '(no files to check)'


def _run_single_hook(filenames, hook, repo, args, skips, cols):
    include, exclude = hook['files'], hook['exclude']
    filenames = _filter_by_include_exclude(filenames, include, exclude)
    types, exclude_types = hook['types'], hook['exclude_types']
    filenames = _filter_by_types(filenames, types, exclude_types)

    if hook['language'] == 'pcre':
        logger.warning(
            '`{}` (from {}) uses the deprecated pcre language.\n'
            'The pcre language is scheduled for removal in pre-commit 2.x.\n'
            'The pygrep language is a more portable (and usually drop-in) '
            'replacement.'.format(hook['id'], repo.repo_config['repo']),
        )

    if hook['id'] in skips:
        output.write(get_hook_message(
            _hook_msg_start(hook, args.verbose),
            end_msg=SKIPPED,
            end_color=color.YELLOW,
            use_color=args.color,
            cols=cols,
        ))
        return 0
    elif not filenames and not hook['always_run']:
        output.write(get_hook_message(
            _hook_msg_start(hook, args.verbose),
            postfix=NO_FILES,
            end_msg=SKIPPED,
            end_color=color.TURQUOISE,
            use_color=args.color,
            cols=cols,
        ))
        return 0

    # Print the hook and the dots first in case the hook takes hella long to
    # run.
    output.write(get_hook_message(
        _hook_msg_start(hook, args.verbose), end_len=6, cols=cols,
    ))
    sys.stdout.flush()

    diff_before = cmd_output(
        'git', 'diff', '--no-ext-diff', retcode=None, encoding=None,
    )
    retcode, stdout, stderr = repo.run_hook(
        hook, tuple(filenames) if hook['pass_filenames'] else (),
    )
    diff_after = cmd_output(
        'git', 'diff', '--no-ext-diff', retcode=None, encoding=None,
    )

    file_modifications = diff_before != diff_after

    # If the hook makes changes, fail the commit
    if file_modifications:
        retcode = 1

    if retcode:
        retcode = 1
        print_color = color.RED
        pass_fail = 'Failed'
    else:
        retcode = 0
        print_color = color.GREEN
        pass_fail = 'Passed'

    output.write_line(color.format_color(pass_fail, print_color, args.color))

    if (
            (stdout or stderr or file_modifications) and
            (retcode or args.verbose or hook['verbose'])
    ):
        output.write_line('hookid: {}\n'.format(hook['id']))

        # Print a message if failing due to file modifications
        if file_modifications:
            output.write('Files were modified by this hook.')

            if stdout or stderr:
                output.write_line(' Additional output:')

            output.write_line()

        for out in (stdout, stderr):
            assert type(out) is bytes, type(out)
            if out.strip():
                output.write_line(out.strip(), logfile_name=hook['log_file'])
        output.write_line()

    return retcode


def _compute_cols(hooks, verbose):
    """Compute the number of columns to display hook messages.  The widest
    that will be displayed is in the no files skipped case:

        Hook name...(no files to check) Skipped

    or in the verbose case

        Hook name [hookid]...(no files to check) Skipped
    """
    if hooks:
        name_len = max(len(_hook_msg_start(hook, verbose)) for hook in hooks)
    else:
        name_len = 0

    cols = name_len + 3 + len(NO_FILES) + 1 + len(SKIPPED)
    return max(cols, 80)


def _all_filenames(args):
    if args.origin and args.source:
        return git.get_changed_files(args.origin, args.source)
    elif args.hook_stage == 'commit-msg':
        return (args.commit_msg_filename,)
    elif args.files:
        return args.files
    elif args.all_files:
        return git.get_all_files()
    elif git.is_in_merge_conflict():
        return git.get_conflicted_files()
    else:
        return git.get_staged_files()


def _run_hooks(config, repo_hooks, args, environ):
    """Actually run the hooks."""
    skips = _get_skips(environ)
    cols = _compute_cols([hook for _, hook in repo_hooks], args.verbose)
    filenames = _all_filenames(args)
    filenames = _filter_by_include_exclude(filenames, '', config['exclude'])
    retval = 0
    for repo, hook in repo_hooks:
        retval |= _run_single_hook(filenames, hook, repo, args, skips, cols)
        if retval and config['fail_fast']:
            break
    if (
            retval and
            args.show_diff_on_failure and
            subprocess.call(('git', 'diff', '--quiet', '--no-ext-diff')) != 0
    ):
        print('All changes made by hooks:')
        subprocess.call(('git', '--no-pager', 'diff', '--no-ext-diff'))
    return retval


def _has_unmerged_paths():
    _, stdout, _ = cmd_output('git', 'ls-files', '--unmerged')
    return bool(stdout.strip())


def _has_unstaged_config(runner):
    retcode, _, _ = cmd_output(
        'git', 'diff', '--no-ext-diff', '--exit-code', runner.config_file_path,
        retcode=None,
    )
    # be explicit, other git errors don't mean it has an unstaged config.
    return retcode == 1


def run(runner, store, args, environ=os.environ):
    no_stash = args.all_files or bool(args.files)

    # Check if we have unresolved merge conflict files and fail fast.
    if _has_unmerged_paths():
        logger.error('Unmerged files.  Resolve before committing.')
        return 1
    if bool(args.source) != bool(args.origin):
        logger.error('Specify both --origin and --source.')
        return 1
    if _has_unstaged_config(runner) and not no_stash:
        logger.error(
            'Your pre-commit configuration is unstaged.\n'
            '`git add {}` to fix this.'.format(runner.config_file),
        )
        return 1

    # Expose origin / source as environment variables for hooks to consume
    if args.origin and args.source:
        environ['PRE_COMMIT_ORIGIN'] = args.origin
        environ['PRE_COMMIT_SOURCE'] = args.source

    if no_stash:
        ctx = noop_context()
    else:
        ctx = staged_files_only(store.directory)

    with ctx:
        repo_hooks = []
        for repo in repositories(runner.config, store):
            for _, hook in repo.hooks:
                if (
                    (not args.hook or hook['id'] == args.hook) and
                    not hook['stages'] or args.hook_stage in hook['stages']
                ):
                    repo_hooks.append((repo, hook))

        if args.hook and not repo_hooks:
            output.write_line('No hook with id `{}`'.format(args.hook))
            return 1

        for repo in {repo for repo, _ in repo_hooks}:
            repo.require_installed()

        return _run_hooks(runner.config, repo_hooks, args, environ)
