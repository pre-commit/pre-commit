from setuptools import setup

setup(
    name='python3_hook',
    version='0.0.0',
    py_modules=['python3_hook'],
    entry_points={'console_scripts': ['python3-hook=python3_hook:main']},
)
