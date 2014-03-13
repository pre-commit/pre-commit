from setuptools import find_packages
from setuptools import setup

setup(
    name='pre_commit',
    version='0.0.0',
    packages=find_packages('.', exclude=('tests*', 'testing*')),
    package_data={
        'pre_commit': [
            'resources/pre-commit.sh'
        ]
    },
    install_requires=[
        'argparse',
        'plumbum',
        'simplejson',
    ],
)
