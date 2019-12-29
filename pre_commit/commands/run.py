from __future__ import unicode_literals

import logging
import os
import re
import subprocess
import time

from identify.identify import tags_from_path

from pre_commit import color
from pre_commit import git
from pre_commit import output
from pre_commit.clientlib import load_config
from pre_commit.output import get_hook_message
from pre_commit.repository import all_hooks
from pre_commit.repository import install_hook_envs
from pre_commit.staged_files_only import staged_files_only
from pre_commit.util import cmd_output_b
from pre_commit.util import noop_context


logger = logging.getLogger('pre_commit')


def filter_by_include_exclude(names, include, exclude):
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    return [
        filename for filename in names
        if include_re.search(filename)
        if not exclude_re.search(filename)
    ]


class Classifier(object):
    def __init__(self, filenames):
        # on windows we normalize all filenames to use forward slashes
        # this makes it easier to filter using the `files:` regex
        # this also makes improperly quoted shell-based hooks work better
        # see #1173
        if os.altsep == '/' and os.sep == '\\':
            filenames = (f.replace(os.sep, os.altsep) for f in filenames)
        self.filenames = [f for f in filenames if os.path.lexists(f)]
        self._types_cache = {}

    def _types_for_file(self, filename):
        try:
            return self._types_cache[filename]
        except KeyError:
            ret = self._types_cache[filename] = tags_from_path(filename)
            return ret

    def by_types(self, names, types, exclude_types):
        types, exclude_types = frozenset(types), frozenset(exclude_types)
        ret = []
        for filename in names:
            tags = self._types_for_file(filename)
            if tags >= types and not tags & exclude_types:
                ret.append(filename)
        return ret

    def filenames_for_hook(self, hook):
        names = self.filenames
        names = filter_by_include_exclude(names, hook.files, hook.exclude)
        names = self.by_types(names, hook.types, hook.exclude_types)
        return names


def _get_skips(environ):
    skips = environ.get('SKIP', '')
    return {skip.strip() for skip in skips.split(',') if skip.strip()}


SKIPPED = 'Skipped'
NO_FILES = '(no files to check)'


def _subtle_line(s, use_color):
    output.write_line(color.format_color(s, color.SUBTLE, use_color))


def _run_single_hook(classifier, hook, skips, cols, verbose, use_color):
    filenames = classifier.filenames_for_hook(hook)

    if hook.language == 'pcre':
        logger.warning(
            '`{}` (from {}) uses the deprecated pcre language.\n'
            'The pcre language is scheduled for removal in pre-commit 2.x.\n'
            'The pygrep language is a more portable (and usually drop-in) '
            'replacement.'.format(hook.id, hook.src),
        )

    if hook.id in skips or hook.alias in skips:
        output.write(
            get_hook_message(
                hook.name,
                end_msg=SKIPPED,
                end_color=color.YELLOW,
                use_color=use_color,
                cols=cols,
            ),
        )
        duration = None
        retcode = 0
        files_modified = False
        out = b''
    elif not filenames and not hook.always_run:
        output.write(
            get_hook_message(
                hook.name,
                postfix=NO_FILES,
                end_msg=SKIPPED,
                end_color=color.TURQUOISE,
                use_color=use_color,
                cols=cols,
            ),
        )
        duration = None
        retcode = 0
        files_modified = False
        out = b''
    else:
        # print hook and dots first in case the hook takes a while to run
        output.write(get_hook_message(hook.name, end_len=6, cols=cols))

        diff_cmd = ('git', 'diff', '--no-ext-diff')
        diff_before = cmd_output_b(*diff_cmd, retcode=None)
        filenames = tuple(filenames) if hook.pass_filenames else ()
        time_before = time.time()
        retcode, out = hook.run(filenames, use_color)
        duration = round(time.time() - time_before, 2) or 0
        diff_after = cmd_output_b(*diff_cmd, retcode=None)

        # if the hook makes changes, fail the commit
        files_modified = diff_before != diff_after

        if retcode or files_modified:
            print_color = color.RED
            status = 'Failed'
        else:
            print_color = color.GREEN
            status = 'Passed'

        output.write_line(color.format_color(status, print_color, use_color))

    if verbose or hook.verbose or retcode or files_modified:
        _subtle_line('- hook id: {}'.format(hook.id), use_color)

        if (verbose or hook.verbose) and duration is not None:
            _subtle_line('- duration: {}s'.format(duration), use_color)

        if retcode:
            _subtle_line('- exit code: {}'.format(retcode), use_color)

        # Print a message if failing due to file modifications
        if files_modified:
            _subtle_line('- files were modified by this hook', use_color)

        if out.strip():
            output.write_line()
            output.write_line(out.strip(), logfile_name=hook.log_file)
            output.write_line()

    return files_modified or bool(retcode)


def _compute_cols(hooks):
    """Compute the number of columns to display hook messages.  The widest
    that will be displayed is in the no files skipped case:

        Hook name...(no files to check) Skipped
    """
    if hooks:
        name_len = max(len(hook.name) for hook in hooks)
    else:
        name_len = 0

    cols = name_len + 3 + len(NO_FILES) + 1 + len(SKIPPED)
    return max(cols, 80)


def _all_filenames(args):
    if args.origin and args.source:
        return git.get_changed_files(args.origin, args.source)
    elif args.hook_stage in {'prepare-commit-msg', 'commit-msg'}:
        return (args.commit_msg_filename,)
    elif args.files:
        return args.files
    elif args.all_files:
        return git.get_all_files()
    elif git.is_in_merge_conflict():
        return git.get_conflicted_files()
    else:
        return git.get_staged_files()


def _run_hooks(config, hooks, args, environ):
    """Actually run the hooks."""
    skips = _get_skips(environ)
    cols = _compute_cols(hooks)
    filenames = _all_filenames(args)
    filenames = filter_by_include_exclude(
        filenames, config['files'], config['exclude'],
    )
    classifier = Classifier(filenames)
    retval = 0
    for hook in hooks:
        retval |= _run_single_hook(
            classifier, hook, skips, cols,
            verbose=args.verbose, use_color=args.color,
        )
        if retval and config['fail_fast']:
            break
    if retval and args.show_diff_on_failure and git.has_diff():
        if args.all_files:
            output.write_line(
                'pre-commit hook(s) made changes.\n'
                'If you are seeing this message in CI, '
                'reproduce locally with: `pre-commit run --all-files`.\n'
                'To run `pre-commit` as part of git workflow, use '
                '`pre-commit install`.',
            )
        output.write_line('All changes made by hooks:')
        # args.color is a boolean.
        # See user_color function in color.py
        subprocess.call((
            'git', '--no-pager', 'diff', '--no-ext-diff',
            '--color={}'.format({True: 'always', False: 'never'}[args.color]),
        ))

    return retval


def _has_unmerged_paths():
    _, stdout, _ = cmd_output_b('git', 'ls-files', '--unmerged')
    return bool(stdout.strip())


def _has_unstaged_config(config_file):
    retcode, _, _ = cmd_output_b(
        'git', 'diff', '--no-ext-diff', '--exit-code', config_file,
        retcode=None,
    )
    # be explicit, other git errors don't mean it has an unstaged config.
    return retcode == 1


def run(config_file, store, args, environ=os.environ):
    no_stash = args.all_files or bool(args.files)

    # Check if we have unresolved merge conflict files and fail fast.
    if _has_unmerged_paths():
        logger.error('Unmerged files.  Resolve before committing.')
        return 1
    if bool(args.source) != bool(args.origin):
        logger.error('Specify both --origin and --source.')
        return 1
    if _has_unstaged_config(config_file) and not no_stash:
        logger.error(
            'Your pre-commit configuration is unstaged.\n'
            '`git add {}` to fix this.'.format(config_file),
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
        config = load_config(config_file)
        hooks = [
            hook
            for hook in all_hooks(config, store)
            if not args.hook or hook.id == args.hook or hook.alias == args.hook
            if args.hook_stage in hook.stages
        ]

        if args.hook and not hooks:
            output.write_line(
                'No hook with id `{}` in stage `{}`'.format(
                    args.hook, args.hook_stage,
                ),
            )
            return 1

        install_hook_envs(hooks, store)

        return _run_hooks(config, hooks, args, environ)
