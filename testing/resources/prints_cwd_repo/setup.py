from setuptools import find_packages
from setuptools import setup

setup(
    name='prints_cwd',
    version='0.0.0',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': ['prints_cwd = prints_cwd.main:func'],
    },
)
