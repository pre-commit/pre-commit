
from pre_commit.languages import node
from pre_commit.languages import python
from pre_commit.languages import ruby

# A language implements the following two functions in its module:
#
# def install_environment():
#     """Installs a repository in the given repository.  Note that the current
#     working directory will already be inside the repository.
#     """
#
# def run_hook(hook, file_args):
#     """Runs a hook and returns the returncode and output of running that hook.
#
#     Returns:
#         (returncode, stdout, stderr)
#     """

languages = {
    'node': node,
    'python': python,
    'ruby': ruby,
}