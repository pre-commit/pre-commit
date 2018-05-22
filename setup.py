from setuptools import find_packages
from setuptools import setup


setup(
    name='pre_commit',
    description=(
        'A framework for managing and maintaining multi-language pre-commit '
        'hooks.'
    ),
    url='https://github.com/pre-commit/pre-commit',
    version='1.9.0',

    author='Anthony Sottile',
    author_email='asottile@umich.edu',

    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],

    packages=find_packages(exclude=('tests*', 'testing*')),
    package_data={
        'pre_commit': [
            'resources/*-tmpl',
            'resources/*.tar.gz',
            'resources/empty_template/*',
            'resources/empty_template/.npmignore',
        ],
    },
    install_requires=[
        'aspy.yaml',
        'cached-property',
        'cfgv>=1.0.0',
        'identify>=1.0.0',
        'nodeenv>=0.11.1',
        'pyyaml',
        'six',
        'virtualenv',
    ],
    entry_points={
        'console_scripts': [
            'pre-commit = pre_commit.main:main',
            'pre-commit-validate-config = pre_commit.clientlib:validate_config_main',  # noqa
            'pre-commit-validate-manifest = pre_commit.clientlib:validate_manifest_main',  # noqa
        ],
    },
)
