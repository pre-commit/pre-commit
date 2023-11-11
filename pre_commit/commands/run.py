from __future__ import annotations

import argparse
import contextlib
import functools
import logging
import os
import re
import subprocess
import time
import unicodedata
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import MutableMapping
from collections.abc import Sequence
from typing import Any

from identify.identify import tags_from_path

from pre_commit import color
from pre_commit import git
from pre_commit import output
from pre_commit.all_languages import languages
from pre_commit.clientlib import load_config
from pre_commit.hook import Hook
from pre_commit.repository import all_hooks
from pre_commit.repository import install_hook_envs
from pre_commit.staged_files_only import staged_files_only
from pre_commit.store import Store
from pre_commit.util import cmd_output_b


logger = logging.getLogger('pre_commit')


def _len_cjk(msg: str) -> int:
    widths = {'A': 1, 'F': 2, 'H': 1, 'N': 1, 'Na': 1, 'W': 2}
    return sum(widths[unicodedata.east_asian_width(c)] for c in msg)


def _start_msg(*, start: str, cols: int, end_len: int) -> str:
    dots = '.' * (cols - _len_cjk(start) - end_len - 1)
    return f'{start}{dots}'


def _full_msg(
        *,
        start: str,
        cols: int,
        end_msg: str,
        end_color: str,
        use_color: bool,
        postfix: str = '',
) -> str:
    dots = '.' * (cols - _len_cjk(start) - len(postfix) - len(end_msg) - 1)
    end = color.format_color(end_msg, end_color, use_color)
    return f'{start}{dots}{postfix}{end}\n'


def filter_by_include_exclude(
        names: Iterable[str],
        include: str,
        exclude: str,
) -> Generator[str, None, None]:
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    return (
        filename for filename in names
        if include_re.search(filename)
        if not exclude_re.search(filename)
    )


class Classifier:
    def __init__(self, filenames: Iterable[str]) -> None:
        self.filenames = [f for f in filenames if os.path.lexists(f)]

    @functools.cache
    def _types_for_file(self, filename: str) -> set[str]:
        return tags_from_path(filename)

    def by_types(
            self,
            names: Iterable[str],
            types: Iterable[str],
            types_or: Iterable[str],
            exclude_types: Iterable[str],
    ) -> Generator[str, None, None]:
        types = frozenset(types)
        types_or = frozenset(types_or)
        exclude_types = frozenset(exclude_types)
        for filename in names:
            tags = self._types_for_file(filename)
            if (
                    tags >= types and
                    (not types_or or tags & types_or) and
                    not tags & exclude_types
            ):
                yield filename

    def filenames_for_hook(self, hook: Hook) -> Generator[str, None, None]:
        return self.by_types(
            filter_by_include_exclude(
                self.filenames,
                hook.files,
                hook.exclude,
            ),
            hook.types,
            hook.types_or,
            hook.exclude_types,
        )

    @classmethod
    def from_config(
            cls,
            filenames: Iterable[str],
            include: str,
            exclude: str,
    ) -> Classifier:
        # on windows we normalize all filenames to use forward slashes
        # this makes it easier to filter using the `files:` regex
        # this also makes improperly quoted shell-based hooks work better
        # see #1173
        if os.altsep == '/' and os.sep == '\\':
            filenames = (f.replace(os.sep, os.altsep) for f in filenames)
        filenames = filter_by_include_exclude(filenames, include, exclude)
        return Classifier(filenames)


def _get_skips(environ: MutableMapping[str, str]) -> set[str]:
    skips = environ.get('SKIP', '')
    return {skip.strip() for skip in skips.split(',') if skip.strip()}


SKIPPED = 'Skipped'
NO_FILES = '(no files to check)'


def _subtle_line(s: str, use_color: bool) -> None:
    output.write_line(color.format_color(s, color.SUBTLE, use_color))


def _run_single_hook(
        classifier: Classifier,
        hook: Hook,
        skips: set[str],
        cols: int,
        diff_before: bytes,
        verbose: bool,
        use_color: bool,
) -> tuple[bool, bytes]:
    filenames = tuple(classifier.filenames_for_hook(hook))

    if hook.id in skips or hook.alias in skips:
        output.write(
            _full_msg(
                start=hook.name,
                end_msg=SKIPPED,
                end_color=color.YELLOW,
                use_color=use_color,
                cols=cols,
            ),
        )
        duration = None
        retcode = 0
        diff_after = diff_before
        files_modified = False
        out = b''
    elif not filenames and not hook.always_run:
        output.write(
            _full_msg(
                start=hook.name,
                postfix=NO_FILES,
                end_msg=SKIPPED,
                end_color=color.TURQUOISE,
                use_color=use_color,
                cols=cols,
            ),
        )
        duration = None
        retcode = 0
        diff_after = diff_before
        files_modified = False
        out = b''
    else:
        # print hook and dots first in case the hook takes a while to run
        output.write(_start_msg(start=hook.name, end_len=6, cols=cols))

        if not hook.pass_filenames:
            filenames = ()
        time_before = time.monotonic()
        language = languages[hook.language]
        with language.in_env(hook.prefix, hook.language_version):
            retcode, out = language.run_hook(
                hook.prefix,
                hook.entry,
                hook.args,
                filenames,
                is_local=hook.src == 'local',
                require_serial=hook.require_serial,
                color=use_color,
            )
        duration = round(time.monotonic() - time_before, 2) or 0
        diff_after = _get_diff()

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
        _subtle_line(f'- hook id: {hook.id}', use_color)

        if (verbose or hook.verbose) and duration is not None:
            _subtle_line(f'- duration: {duration}s', use_color)

        if retcode:
            _subtle_line(f'- exit code: {retcode}', use_color)

        # Print a message if failing due to file modifications
        if files_modified:
            _subtle_line('- files were modified by this hook', use_color)

        if out.strip():
            output.write_line()
            output.write_line_b(out.strip(), logfile_name=hook.log_file)
            output.write_line()

    return files_modified or bool(retcode), diff_after


def _compute_cols(hooks: Sequence[Hook]) -> int:
    """Compute the number of columns to display hook messages.  The widest
    that will be displayed is in the no files skipped case:

        Hook name...(no files to check) Skipped
    """
    if hooks:
        name_len = max(_len_cjk(hook.name) for hook in hooks)
    else:
        name_len = 0

    cols = name_len + 3 + len(NO_FILES) + 1 + len(SKIPPED)
    return max(cols, 80)


def _all_filenames(args: argparse.Namespace) -> Iterable[str]:
    # these hooks do not operate on files
    if args.hook_stage in {
        'post-checkout', 'post-commit', 'post-merge', 'post-rewrite',
        'pre-rebase',
    }:
        return ()
    elif args.hook_stage in {'prepare-commit-msg', 'commit-msg'}:
        return (args.commit_msg_filename,)
    elif args.from_ref and args.to_ref:
        return git.get_changed_files(args.from_ref, args.to_ref)
    elif args.files:
        return args.files
    elif args.all_files:
        return git.get_all_files()
    elif git.is_in_merge_conflict():
        return git.get_conflicted_files()
    else:
        return git.get_staged_files()


def _get_diff() -> bytes:
    _, out, _ = cmd_output_b(
        'git', 'diff', '--no-ext-diff', '--no-textconv', '--ignore-submodules',
        check=False,
    )
    return out


def _run_hooks(
        config: dict[str, Any],
        hooks: Sequence[Hook],
        skips: set[str],
        args: argparse.Namespace,
) -> int:
    """Actually run the hooks."""
    cols = _compute_cols(hooks)
    classifier = Classifier.from_config(
        _all_filenames(args), config['files'], config['exclude'],
    )
    retval = 0
    prior_diff = _get_diff()
    for hook in hooks:
        current_retval, prior_diff = _run_single_hook(
            classifier, hook, skips, cols, prior_diff,
            verbose=args.verbose, use_color=args.color,
        )
        retval |= current_retval
        if retval and (config['fail_fast'] or hook.fail_fast):
            break
    if retval and args.show_diff_on_failure and prior_diff:
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
        git_color_opt = 'always' if args.color else 'never'
        subprocess.call((
            'git', '--no-pager', 'diff', '--no-ext-diff',
            f'--color={git_color_opt}',
        ))

    return retval


def _has_unmerged_paths() -> bool:
    _, stdout, _ = cmd_output_b('git', 'ls-files', '--unmerged')
    return bool(stdout.strip())


def _has_unstaged_config(config_file: str) -> bool:
    retcode = 0
    if os.path.islink(config_file):
        real_config_file = os.path.realpath(config_file)
        _, is_real_file_in_git_dir, _, = cmd_output_b(
            'git', 'ls-files', config_file,
        )
        if is_real_file_in_git_dir:
            cmd = ('git', 'diff', '--quiet', '--no-ext-diff', real_config_file)
            retcode, _, _ = cmd_output_b(*cmd, check=False)
    else:
        cmd = ('git', 'diff', '--quiet', '--no-ext-diff', config_file)
        retcode, _, _ = cmd_output_b(*cmd, check=False)
    # be explicit, other git errors don't mean it has an unstaged config.
    return retcode == 1


def run(
        config_file: str,
        store: Store,
        args: argparse.Namespace,
        environ: MutableMapping[str, str] = os.environ,
) -> int:
    stash = not args.all_files and not args.files

    # Check if we have unresolved merge conflict files and fail fast.
    if stash and _has_unmerged_paths():
        logger.error('Unmerged files.  Resolve before committing.')
        return 1
    if bool(args.from_ref) != bool(args.to_ref):
        logger.error('Specify both --from-ref and --to-ref.')
        return 1
    if stash and _has_unstaged_config(config_file):
        logger.error(
            f'Your pre-commit configuration is unstaged.\n'
            f'`git add {config_file}` to fix this.',
        )
        return 1
    if (
            args.hook_stage in {'prepare-commit-msg', 'commit-msg'} and
            not args.commit_msg_filename
    ):
        logger.error(
            f'`--commit-msg-filename` is required for '
            f'`--hook-stage {args.hook_stage}`',
        )
        return 1
    # prevent recursive post-checkout hooks (#1418)
    if (
            args.hook_stage == 'post-checkout' and
            environ.get('_PRE_COMMIT_SKIP_POST_CHECKOUT')
    ):
        return 0

    # Expose prepare_commit_message_source / commit_object_name
    # as environment variables for the hooks
    if args.prepare_commit_message_source:
        environ['PRE_COMMIT_COMMIT_MSG_SOURCE'] = (
            args.prepare_commit_message_source
        )

    if args.commit_object_name:
        environ['PRE_COMMIT_COMMIT_OBJECT_NAME'] = args.commit_object_name

    # Expose from-ref / to-ref as environment variables for hooks to consume
    if args.from_ref and args.to_ref:
        # legacy names
        environ['PRE_COMMIT_ORIGIN'] = args.from_ref
        environ['PRE_COMMIT_SOURCE'] = args.to_ref
        # new names
        environ['PRE_COMMIT_FROM_REF'] = args.from_ref
        environ['PRE_COMMIT_TO_REF'] = args.to_ref

    if args.pre_rebase_upstream and args.pre_rebase_branch:
        environ['PRE_COMMIT_PRE_REBASE_UPSTREAM'] = args.pre_rebase_upstream
        environ['PRE_COMMIT_PRE_REBASE_BRANCH'] = args.pre_rebase_branch

    if (
        args.remote_name and args.remote_url and
        args.remote_branch and args.local_branch
    ):
        environ['PRE_COMMIT_LOCAL_BRANCH'] = args.local_branch
        environ['PRE_COMMIT_REMOTE_BRANCH'] = args.remote_branch
        environ['PRE_COMMIT_REMOTE_NAME'] = args.remote_name
        environ['PRE_COMMIT_REMOTE_URL'] = args.remote_url

    if args.checkout_type:
        environ['PRE_COMMIT_CHECKOUT_TYPE'] = args.checkout_type

    if args.is_squash_merge:
        environ['PRE_COMMIT_IS_SQUASH_MERGE'] = args.is_squash_merge

    if args.rewrite_command:
        environ['PRE_COMMIT_REWRITE_COMMAND'] = args.rewrite_command

    # Set pre_commit flag
    environ['PRE_COMMIT'] = '1'

    with contextlib.ExitStack() as exit_stack:
        if stash:
            exit_stack.enter_context(staged_files_only(store.directory))

        config = load_config(config_file)
        hooks = [
            hook
            for hook in all_hooks(config, store)
            if not args.hook or hook.id == args.hook or hook.alias == args.hook
            if args.hook_stage in hook.stages
        ]

        if args.hook and not hooks:
            output.write_line(
                f'No hook with id `{args.hook}` in stage `{args.hook_stage}`',
            )
            return 1

        skips = _get_skips(environ)
        to_install = [
            hook
            for hook in hooks
            if hook.id not in skips and hook.alias not in skips
        ]
        install_hook_envs(to_install, store)

        return _run_hooks(config, hooks, skips, args)

    # https://github.com/python/mypy/issues/7726
    raise AssertionError('unreachable')
