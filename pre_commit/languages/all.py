from __future__ import unicode_literals

from pre_commit.languages import node
from pre_commit.languages import pcre
from pre_commit.languages import python
from pre_commit.languages import ruby
from pre_commit.languages import script
from pre_commit.languages import system

# A language implements the following constant and two functions in its module:
#
# # Use None for no environment
# ENVIRONMENT_DIR = 'foo_env'
#
# def install_environment(
#         repo_cmd_runner,
#         version='default',
#         additional_dependencies=(),
# ):
#     """Installs a repository in the given repository.  Note that the current
#     working directory will already be inside the repository.
#
#     Args:
#         repo_cmd_runner - `PrefixedCommandRunner` bound to the repository.
#         version - A version specified in the hook configuration or
#             'default'.
#     """
#
# def run_hook(repo_cmd_runner, hook, file_args):
#     """Runs a hook and returns the returncode and output of running that
#     hook.
#
#     Args:
#         repo_cmd_runner - `PrefixedCommandRunner` bound to the repository.
#         hook - Hook dictionary
#         file_args - The files to be run
#
#     Returns:
#         (returncode, stdout, stderr)
#     """

languages = {
    'node': node,
    'pcre': pcre,
    'python': python,
    'ruby': ruby,
    'script': script,
    'system': system,
}


all_languages = languages.keys()
