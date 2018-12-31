from __future__ import unicode_literals

from pre_commit.languages import helpers


ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(hook, file_args):
    return helpers.run_xargs(hook, helpers.to_cmd(hook), file_args)
