from setuptools import find_packages
from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

setup(
    name='pre_commit',
    description=(
        'A framework for managing and maintaining multi-language pre-commit '
        'hooks.'
    ),
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pre-commit/pre-commit',
    version='1.14.0',
    author='Anthony Sottile',
    author_email='asottile@umich.edu',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    packages=find_packages(exclude=('tests*', 'testing*')),
    package_data={
        'pre_commit.resources': [
            '*.tar.gz',
            'empty_template_*',
            'hook-tmpl',
        ],
    },
    install_requires=[
        'aspy.yaml',
        'cfgv>=1.4.0',
        'identify>=1.0.0',
        # if this makes it into python3.8 move to extras_require
        'importlib-metadata',
        'nodeenv>=0.11.1',
        'pyyaml',
        'six',
        'toml',
        'virtualenv',
    ],
    extras_require={
        ':python_version<"3.2"': ['futures'],
        ':python_version<"3.7"': ['importlib-resources'],
    },
    entry_points={
        'console_scripts': [
            'pre-commit = pre_commit.main:main',
            'pre-commit-validate-config = pre_commit.clientlib:validate_config_main',  # noqa
            'pre-commit-validate-manifest = pre_commit.clientlib:validate_manifest_main',  # noqa
        ],
    },
)
