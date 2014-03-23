
import pytest

import pre_commit.constants as C
from pre_commit.languages.all import languages


def test_all_languages_have_repo_setups():
    assert set(languages.keys()) == C.SUPPORTED_LANGUAGES


@pytest.mark.parametrize('language', C.SUPPORTED_LANGUAGES)
def test_all_languages_support_interface(language):
    assert hasattr(languages[language], 'install_environment')
    assert hasattr(languages[language], 'run_hook')
