from __future__ import annotations

from setuptools import setup

setup(
    name='foo',
    version='0.0.0',
    py_modules=['foo'],
    entry_points={'console_scripts': ['foo = foo:main']},
)
