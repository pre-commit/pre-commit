from setuptools import find_packages
from setuptools import setup

setup(
    name='pre_commit',
    version='0.0.0',
    packages=find_packages('.', exclude=('tests*', 'testing*')),
    install_requires=[
        'argparse',
        'jsonschema',
        'plumbum',
        'pyyaml',
        'simplejson',
    ],
    entry_points={
        'console_scripts': [
            'pre-commit = pre_commit.entry_points:pre_commit_func',
            'validate-manifest = pre_commit.entry_points:validate_manifest_func',
        ],
    }
)
