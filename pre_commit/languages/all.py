from __future__ import unicode_literals

from pre_commit.languages import docker
from pre_commit.languages import docker_image
from pre_commit.languages import golang
from pre_commit.languages import node
from pre_commit.languages import pcre
from pre_commit.languages import pygrep
from pre_commit.languages import python
from pre_commit.languages import python_venv
from pre_commit.languages import ruby
from pre_commit.languages import rust
from pre_commit.languages import script
from pre_commit.languages import swift
from pre_commit.languages import system

# A language implements the following constant and functions in its module:
#
# # Use None for no environment
# ENVIRONMENT_DIR = 'foo_env'
#
# def get_default_version():
#     """Return a value to replace the 'default' value for language_version.
#
#     return 'default' if there is no better option.
#    """
#
# def healthy(prefix, language_version):
#     """Return whether or not the environment is considered functional."""
#
# def install_environment(prefix, version, additional_dependencies):
#     """Installs a repository in the given repository.  Note that the current
#     working directory will already be inside the repository.
#
#     Args:
#         prefix - `Prefix` bound to the repository.
#         version - A version specified in the hook configuration or
#             'default'.
#     """
#
# def run_hook(prefix, hook, file_args):
#     """Runs a hook and returns the returncode and output of running that
#     hook.
#
#     Args:
#         prefix - `Prefix` bound to the repository.
#         hook - Hook dictionary
#         file_args - The files to be run
#
#     Returns:
#         (returncode, stdout, stderr)
#     """

languages = {
    'docker': docker,
    'docker_image': docker_image,
    'golang': golang,
    'node': node,
    'pcre': pcre,
    'pygrep': pygrep,
    'python': python,
    'python_venv': python_venv,
    'ruby': ruby,
    'rust': rust,
    'script': script,
    'swift': swift,
    'system': system,
}
all_languages = sorted(languages)
