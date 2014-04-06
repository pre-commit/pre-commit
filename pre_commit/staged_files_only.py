
import contextlib
import time

from pre_commit.prefixed_command_runner import CalledProcessError


@contextlib.contextmanager
def staged_files_only(cmd_runner):
    """Clear any unstaged changes from the git working directory inside this
    context.

    Args:
        cmd_runner - PrefixedCommandRunner
    """
    # Determine if there are unstaged files
    retcode, _, _ = cmd_runner.run(
        ['git', 'diff-files', '--quiet'],
        retcode=None,
    )
    if retcode:
        # TODO: print a warning message that unstaged things are being stashed
        # Save the current unstaged changes as a patch
        # TODO: use a more unique patch filename
        patch_filename = cmd_runner.path('patch{0}'.format(time.time()))
        with open(patch_filename, 'w') as patch_file:
            cmd_runner.run(['git', 'diff', '--binary'], stdout=patch_file)

        # Clear the working directory of unstaged changes
        cmd_runner.run(['git', 'checkout', '--', '.'])
        try:
            yield
        finally:
            # Try to apply the patch we saved
            try:
                cmd_runner.run(['git', 'apply', patch_filename])
            except CalledProcessError:
                # TOOD: print a warning about rolling back changes made by hooks
                # We failed to apply the patch, presumably due to fixes made
                # by hooks.
                # Roll back the changes made by hooks.
                cmd_runner.run(['git', 'checkout', '--', '.'])
                cmd_runner.run(['git', 'apply', patch_filename])
    else:
        # There weren't any staged files so we don't need to do anything
        # special
        yield
