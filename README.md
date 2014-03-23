[![Build Status](https://travis-ci.org/pre-commit/pre-commit.svg?branch=master)](https://travis-ci.org/pre-commit/pre-commit)

pre-commit
==========

A framework for managing and maintaining multi-language pre-commit hooks.

Some out-of-the-box hooks: https://github.com/pre-commit/pre-commit-hooks


## What is a "pre-commit"

A pre-commit is some code that runs before commiting code to do some spot-checking for some basic programming mistakes.

## Why make this project?

We noticed that when creating a git repo it was not convenient to create pre-commit hooks.  Often we resorted to copy/paste to include a set of useful hooks. https://github.com/causes/overcommit is an awesome project, but locked us into ruby and system packages -- which we wanted to avoid.
