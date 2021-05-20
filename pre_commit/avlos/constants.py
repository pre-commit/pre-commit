from pathlib import Path

HOME_DIRECTORY = str(Path.home())
CONFIG_FILE = '.pre-commit-config.yaml'
DEFAULT_CONFIG_FILE = HOME_DIRECTORY + '/' + CONFIG_FILE
GITHUB_DOTFILES_REPOSITORY = 'https://github.com/avlos/dotfiles/'
GITHUB_DOTFILES_REPOSITORY_BRANCH = 'some_branch_to_get_from_command_flag_for_development'
