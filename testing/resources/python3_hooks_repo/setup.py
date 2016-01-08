# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

setup(
    name='python3_hook',
    version='0.0.0',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': ['python3-hook = python3_hook.main:func'],
    },
)
