import logging
import os.path

from pre_commit.commands.install_uninstall import install
from pre_commit.util import cmd_output

logger = logging.getLogger('pre_commit')


def init_templatedir(config_file, store, directory, hook_type):
    install(
        config_file, store, overwrite=True, hook_type=hook_type,
        skip_on_missing_config=True, git_dir=directory,
    )
    _, out, _ = cmd_output('git', 'config', 'init.templateDir', retcode=None)
    dest = os.path.realpath(directory)
    if os.path.realpath(out.strip()) != dest:
        logger.warning('`init.templateDir` not set to the target directory')
        logger.warning(
            'maybe `git config --global init.templateDir {}`?'.format(dest),
        )
