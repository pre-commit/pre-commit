import itertools
import logging
import os.path
import shutil
import sys
from typing import Optional
from typing import Sequence
from typing import Tuple

from pre_commit import git
from pre_commit import output
from pre_commit.clientlib import load_config
from pre_commit.repository import all_hooks
from pre_commit.repository import install_hook_envs
from pre_commit.store import Store
from pre_commit.util import make_executable
from pre_commit.util import resource_text
from pre_commit.commands.install_uninstall import _install_hook_script
from pre_commit.commands.install_uninstall import _hook_paths

# import avlos github with dotfiles #
from pathlib import Path
from git.repo.base import Repo
from pre_commit.avlos.constants import GITHUB_DOTFILES_REPOSITORY

logger = logging.getLogger(__name__)

##################################
### Avlos installation scripts ###
##################################
def setup_avlos() -> int:
    """
    Installs the remote repository with dotfiles
    and copies them over to home directory
    """
    ### install github repository ###
    home_directory = str(Path.home())
    installation_directory = home_directory + '/.dotfiles'
    logger.info(
        "Cloning git repository {} to {}".format(GITHUB_DOTFILES_REPOSITORY, installation_directory)
    )
    # check if folder exists, remove #
    if os.path.isdir(installation_directory):
        shutil.rmtree(installation_directory)
    Repo.clone_from(GITHUB_DOTFILES_REPOSITORY, installation_directory)

    ### copy dotfiles to home directory ###
    dotfiles = os.listdir(installation_directory)
    dotfiles = [d for d in dotfiles if d.startswith('.') and d not in ['.git', '.gitignore']]

    # check for existing dotfiles #
    existing_dotfiles = list(set(os.listdir(home_directory)) & set(dotfiles))
    if len(existing_dotfiles) > 0:
        logger.warning(
            "The configuration files {} already exist.".format(", ".join(existing_dotfiles))
        )
        answer = input("Overwrite? (Y/N): ")
        if not answer.lower().startswith('y'):
            dotfiles = list(set(dotfiles) - set(existing_dotfiles))

    # copy to home directory
    for dotfile in dotfiles:
        shutil.copyfile(installation_directory + '/' + dotfile, home_directory + '/' + dotfile)

    logger.info("Pre-commit configuration installed.")
    return 0

def install_avlos(
    store: Store,
    hook_types: Sequence[str],
    overwrite: bool = False,
    hooks: bool = False,
    skip_on_missing_config: bool = False,
    git_dir: Optional[str] = None,
) -> int:
    """
    Installs the remote repository with dotfiles
    and copies them over to home directory
    """
    ### install github repository ###
    logger.info("Installing hooks at git repository")
    home_directory = str(Path.home())

    installation_directory = home_directory + '/.dotfiles'
    if os.path.isdir(installation_directory):
        logger.warning("The configuration repository ~/.dotfiles already exists. If you want to update it run `pre-commit avlos-setup`")
    else:
        setup_avlos()

    config_file = home_directory + '/.pre-commit-config.yaml'

    for hook_type in hook_types:
        _install_hook_script(
            config_file,
            hook_type,
            overwrite=overwrite,
            skip_on_missing_config=skip_on_missing_config,
            git_dir=git_dir,
        )

    if hooks:
        install_hooks(config_file, store)

    return 0
