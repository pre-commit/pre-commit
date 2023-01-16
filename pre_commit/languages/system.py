from __future__ import annotations

from pre_commit.languages import helpers

ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check
install_environment = helpers.no_install
in_env = helpers.no_env
run_hook = helpers.basic_run_hook
