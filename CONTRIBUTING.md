# Contributing

## Local development

- The complete test suite depends on having at least the following installed (possibly not
  a complete list)
  - git (A sufficiently newer version is required to run pre-push tests)
  - python
  - python3.4 (Required by a test which checks different python versions)
  - python3.5 (Required by a test which checks different python versions)
  - tox (or virtualenv)
  - ruby + gem
  - docker

### Setting up an environemnt

This is useful for running specific tests.  The easiest way to set this up
is to run:

1. `tox -e venv`
2. `. venv-pre_commit/bin/activate`

This will create and put you into a virtualenv which has an editable
installation of pre-commit.  Hack away!  Running `pre-commit` will reflect
your changes immediately.

### Running a specific test

Running a specific test with the environment activated is as easy as:
`py.test tests -k test_the_name_of_your_test`

### Running all the tests

Running all the tests can be done by running `tox -e py27` (or your
interpreter version of choice).  These often take a long time and consume
significant cpu while running the slower node / ruby integration tests.

Alternatively, with the environment activated you can run all of the tests
using:
`py.test tests`

### Setting up the hooks

With the environment activated simply run `pre-commit install`.

## Documentation

Documentation is hosted at http://pre-commit.com

This website is controlled through
https://github.com/pre-commit/pre-commit.github.io

When adding a feature, please make a pull request to add yourself to the
contributors list and add documentation to the website if applicable.
