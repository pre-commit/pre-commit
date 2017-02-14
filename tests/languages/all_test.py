from __future__ import unicode_literals

import inspect

import pytest

from pre_commit.languages.all import all_languages
from pre_commit.languages.all import languages


@pytest.mark.parametrize('language', all_languages)
def test_install_environment_argspec(language):
    expected_argspec = inspect.ArgSpec(
        args=[
            'repo_cmd_runner',
            'version',
            'additional_dependencies',
            'is_local_hook',
        ],
        varargs=None,
        keywords=None,
        defaults=('default', (), False),
    )
    argspec = inspect.getargspec(languages[language].install_environment)
    assert argspec == expected_argspec


@pytest.mark.parametrize('language', all_languages)
def test_ENVIRONMENT_DIR(language):
    assert hasattr(languages[language], 'ENVIRONMENT_DIR')


@pytest.mark.parametrize('language', all_languages)
def test_run_hook_argpsec(language):
    expected_argspec = inspect.ArgSpec(
        args=['repo_cmd_runner', 'hook', 'file_args'],
        varargs=None, keywords=None, defaults=None,
    )
    argspec = inspect.getargspec(languages[language].run_hook)
    assert argspec == expected_argspec
