# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

setup(
    name='Foo',
    version='0.0.0',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': ['foo = foo.main:func'],
    },
)
