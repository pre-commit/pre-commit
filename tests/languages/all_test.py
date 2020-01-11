import inspect
from typing import Sequence
from typing import Tuple

import pytest

from pre_commit.languages.all import all_languages
from pre_commit.languages.all import languages
from pre_commit.prefix import Prefix


def _argspec(annotations):
    args = [k for k in annotations if k != 'return']
    return inspect.FullArgSpec(
        args=args, annotations=annotations,
        varargs=None, varkw=None, defaults=None,
        kwonlyargs=[], kwonlydefaults=None,
    )


@pytest.mark.parametrize('language', all_languages)
def test_install_environment_argspec(language):
    expected_argspec = _argspec({
        'return': None,
        'prefix': Prefix,
        'version': str,
        'additional_dependencies': Sequence[str],
    })
    argspec = inspect.getfullargspec(languages[language].install_environment)
    assert argspec == expected_argspec


@pytest.mark.parametrize('language', all_languages)
def test_ENVIRONMENT_DIR(language):
    assert hasattr(languages[language], 'ENVIRONMENT_DIR')


@pytest.mark.parametrize('language', all_languages)
def test_run_hook_argspec(language):
    expected_argspec = _argspec({
        'return': Tuple[int, bytes],
        'hook': 'Hook', 'file_args': Sequence[str], 'color': bool,
    })
    argspec = inspect.getfullargspec(languages[language].run_hook)
    assert argspec == expected_argspec


@pytest.mark.parametrize('language', all_languages)
def test_get_default_version_argspec(language):
    expected_argspec = _argspec({'return': str})
    argspec = inspect.getfullargspec(languages[language].get_default_version)
    assert argspec == expected_argspec


@pytest.mark.parametrize('language', all_languages)
def test_healthy_argspec(language):
    expected_argspec = _argspec({
        'return': bool,
        'prefix': Prefix, 'language_version': str,
    })
    argspec = inspect.getfullargspec(languages[language].healthy)
    assert argspec == expected_argspec
