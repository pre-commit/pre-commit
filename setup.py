import sys
from setuptools import find_packages
from setuptools import setup


install_requires = [
    'argparse',
    'jsonschema',
    'plumbum',
    'pyyaml',
    'simplejson',
]


if sys.version_info < (2, 7):
    install_requires.append('ordereddict')


setup(
    name='pre_commit',
    version='0.0.0',
    packages=find_packages('.', exclude=('tests*', 'testing*')),
    package_data={
        'pre_commit': [
            'resources/pre-commit.sh'
        ]
    },
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'pre-commit = pre_commit.run:run',
            'validate-config = pre_commit.clientlib.validate_config:run',
            'validate-manifest = pre_commit.clientlib.validate_manifest:run',
        ],
    },
    scripts=[
        'scripts/__rvm-env.sh',
    ],
)
