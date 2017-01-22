from __future__ import unicode_literals

import logging
import os.path

from cached_property import cached_property

import pre_commit.constants as C
from pre_commit.clientlib.validate_manifest import load_manifest


logger = logging.getLogger('pre_commit')


class Manifest(object):
    def __init__(self, repo_path_getter, repo_url):
        self.repo_path_getter = repo_path_getter
        self.repo_url = repo_url

    @cached_property
    def manifest_contents(self):
        repo_path = self.repo_path_getter.repo_path
        default_path = os.path.join(repo_path, C.MANIFEST_FILE)
        legacy_path = os.path.join(repo_path, C.MANIFEST_FILE_LEGACY)
        if os.path.exists(default_path):
            return load_manifest(default_path)
        else:
            logger.warning(
                '{} uses legacy {} to provide hooks.\n'
                'In newer versions, this file is called {}\n'
                'This will work in this version of pre-commit but will be '
                'removed at a later time.\n'
                'If `pre-commit autoupdate` does not silence this warning '
                'consider making an issue / pull request.'.format(
                    self.repo_url, C.MANIFEST_FILE_LEGACY, C.MANIFEST_FILE,
                )
            )
            return load_manifest(legacy_path)

    @cached_property
    def hooks(self):
        return {hook['id']: hook for hook in self.manifest_contents}
