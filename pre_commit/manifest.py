from __future__ import unicode_literals

import os.path

from cached_property import cached_property

import pre_commit.constants as C
from pre_commit.clientlib import load_manifest


class Manifest(object):
    def __init__(self, repo_path):
        self.repo_path = repo_path

    @cached_property
    def manifest_contents(self):
        return load_manifest(os.path.join(self.repo_path, C.MANIFEST_FILE))

    @cached_property
    def hooks(self):
        return {hook['id']: hook for hook in self.manifest_contents}
