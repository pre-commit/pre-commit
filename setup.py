from setuptools import find_packages
from setuptools import setup


setup(
    name='pre_commit',
    description=(
        'A framework for managing and maintaining multi-language pre-commit '
        'hooks.'
    ),
    url='https://github.com/pre-commit/pre-commit',
    version='0.2.8',

    author='Anthony Sottile',
    author_email='asottile@umich.edu',

    platforms='linux',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    packages=find_packages('.', exclude=('tests*', 'testing*')),
    package_data={
        'pre_commit': [
            'resources/pre-commit-hook',
            'resources/rbenv.tar.gz',
            'resources/ruby-build.tar.gz',
            'resources/ruby-download.tar.gz',
        ]
    },
    install_requires=[
        'argparse',
        'aspy.yaml',
        'cached-property',
        'jsonschema',
        'nodeenv>=0.9.4',
        'ordereddict',
        'plumbum',
        'pyyaml',
        'simplejson',
        'virtualenv',
    ],
    entry_points={
        'console_scripts': [
            'pre-commit = pre_commit.main:main',
            'validate-config = pre_commit.clientlib.validate_config:run',
            'validate-manifest = pre_commit.clientlib.validate_manifest:run',
        ],
    },
)
