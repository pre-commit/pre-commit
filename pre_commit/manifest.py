from __future__ import unicode_literals

import os.path

from cached_property import cached_property

import pre_commit.constants as C
from pre_commit.clientlib.validate_manifest import load_manifest


class Manifest(object):
    def __init__(self, repo_path_getter):
        self.repo_path_getter = repo_path_getter

    @cached_property
    def manifest_contents(self):
        manifest_path = os.path.join(
            self.repo_path_getter.repo_path, C.MANIFEST_FILE,
        )
        return load_manifest(manifest_path)

    @cached_property
    def hooks(self):
        return dict((hook['id'], hook) for hook in self.manifest_contents)
