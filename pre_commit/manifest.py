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
        return load_manifest(os.path.join(self.repo_path, C.MANIFEST_FILE))

    @cached_property
    def hooks(self):
        ret = {}
        for hook in self.manifest_contents:
            if hook['language_version'] == 'default':
                language = languages[hook['language']]
                hook['language_version'] = language.get_default_version()
            ret[hook['id']] = hook
        return ret
