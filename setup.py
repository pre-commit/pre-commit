from setuptools import find_packages
from setuptools import setup

setup(
    name='pre_commit',
    version='0.0.0',
    packages=find_packages('.', exclude=('tests*', 'testing*')),
    install_requires=[
        'argparse',
        'plumbum',
        'simplejson',
    ],
    scripts=[
        'scripts/pre-commit.py',
    ],
)
