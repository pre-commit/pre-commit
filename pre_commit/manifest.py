from __future__ import unicode_literals

import os.path

from cached_property import cached_property

import pre_commit.constants as C
from pre_commit.clientlib.validate_manifest import load_manifest


class BaseManifest(object):
    def __init__(self):
        pass

    @cached_property
    def manifest_contents(self):
        return load_manifest(self.manifest_path)

    @cached_property
    def hooks(self):
        return dict((hook['id'], hook) for hook in self.manifest_contents)

    def exists(self):
        return os.path.isfile(self.manifest_path)


class Manifest(BaseManifest):
    def __init__(self, repo_path_getter):
        super(Manifest, self).__init__()

        self.repo_path_getter = repo_path_getter
        self.manifest_path = os.path.join(
            self.repo_path_getter.repo_path, C.MANIFEST_FILE,
        )


class ExternalManifest(BaseManifest):
    def __init__(self, path):
        super(ExternalManifest, self).__init__()
        self.path = path
        self.manifest_path = os.path.join(path, C.EXTERNAL_MANIFEST_FILE)
