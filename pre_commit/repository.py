from asottile.ordereddict import OrderedDict

from pre_commit.languages.all import languages
from pre_commit.manifest import Manifest
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.util import cached_property


class Repository(object):
    def __init__(self, repo_config, repo_path_getter):
        self.repo_config = repo_config
        self.repo_path_getter = repo_path_getter
        self.__installed = False

    @classmethod
    def create(cls, config, store):
        repo_path_getter = store.get_repo_path_getter(
            config['repo'], config['sha']
        )
        return cls(config, repo_path_getter)

    @cached_property
    def repo_url(self):
        return self.repo_config['repo']

    @cached_property
    def sha(self):
        return self.repo_config['sha']

    @cached_property
    def languages(self):
        return set(hook['language'] for hook in self.hooks.values())

    @cached_property
    def hooks(self):
        # TODO: merging in manifest dicts is a smell imo
        return OrderedDict(
            (hook['id'], dict(hook, **self.manifest.hooks[hook['id']]))
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def manifest(self):
        return Manifest(self.repo_path_getter)

    def get_cmd_runner(self, hooks_cmd_runner):
        # TODO: this effectively throws away the original cmd runner
        return PrefixedCommandRunner.from_command_runner(
            hooks_cmd_runner, self.repo_path_getter.repo_path,
        )

    def require_installed(self, cmd_runner):
        if self.__installed:
            return

        self.install(cmd_runner)
        self.__installed = True

    def install(self, cmd_runner):
        """Install the hook repository.

        Args:
            cmd_runner - A `PrefixedCommandRunner` bound to the hooks workspace
        """
        repo_cmd_runner = self.get_cmd_runner(cmd_runner)
        for language_name in self.languages:
            language = languages[language_name]
            if (
                language.ENVIRONMENT_DIR is None or
                repo_cmd_runner.exists(language.ENVIRONMENT_DIR)
            ):
                # The language is already installed
                continue
            language.install_environment(repo_cmd_runner)

    def run_hook(self, cmd_runner, hook_id, file_args):
        """Run a hook.

        Args:
            cmd_runner - A `PrefixedCommandRunner` bound to the hooks workspace
            hook_id - Id of the hook
            file_args - List of files to run
        """
        self.require_installed(cmd_runner)
        repo_cmd_runner = self.get_cmd_runner(cmd_runner)
        hook = self.hooks[hook_id]
        return languages[hook['language']].run_hook(
            repo_cmd_runner, hook, file_args,
        )
