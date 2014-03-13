
import pytest
from plumbum import local


@pytest.yield_fixture
def empty_git_dir(tmpdir):
    with local.cwd(tmpdir.strpath):
        local['git']['init']()
        yield tmpdir.strpath