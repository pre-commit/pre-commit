from pre_commit.languages import helpers


ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(hook, file_args, color):
    return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
