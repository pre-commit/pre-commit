
import pytest

from pre_commit.languages.all import all_languages
from pre_commit.languages.all import languages


@pytest.mark.parametrize('language', all_languages)
def test_all_languages_support_interface(language):
    assert hasattr(languages[language], 'install_environment')
    assert hasattr(languages[language], 'run_hook')
