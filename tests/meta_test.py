import io

import pre_commit.constants as C


def test_hooks_yaml_same_contents():
    legacy_contents = io.open(C.MANIFEST_FILE_LEGACY).read()
    contents = io.open(C.MANIFEST_FILE).read()
    assert legacy_contents == contents
