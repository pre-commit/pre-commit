from __future__ import unicode_literals

import logging
import os.path

from cached_property import cached_property

import pre_commit.constants as C
from pre_commit.clientlib import load_manifest
from pre_commit.languages.all import languages


logger = logging.getLogger('pre_commit')


class Manifest(object):
    def __init__(self, repo_path, repo_url):
        self.repo_path = repo_path
        self.repo_url = repo_url

    @cached_property
    def manifest_contents(self):
        default_path = os.path.join(self.repo_path, C.MANIFEST_FILE)
        legacy_path = os.path.join(self.repo_path, C.MANIFEST_FILE_LEGACY)
        if os.path.exists(legacy_path) and not os.path.exists(default_path):
            logger.warning(
                '{} uses legacy {} to provide hooks.\n'
                'In newer versions, this file is called {}\n'
                'This will work in this version of pre-commit but will be '
                'removed at a later time.\n'
                'If `pre-commit autoupdate` does not silence this warning '
                'consider making an issue / pull request.'.format(
                    self.repo_url, C.MANIFEST_FILE_LEGACY, C.MANIFEST_FILE,
                ),
            )
            return load_manifest(legacy_path)
        else:
            return load_manifest(default_path)

    @cached_property
    def hooks(self):
        ret = {}
        for hook in self.manifest_contents:
            if hook['language_version'] == 'default':
                language = languages[hook['language']]
                hook['language_version'] = language.get_default_version()
            ret[hook['id']] = hook
        return ret
