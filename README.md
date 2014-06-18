[![Build Status](https://travis-ci.org/pre-commit/pre-commit.svg?branch=master)](https://travis-ci.org/pre-commit/pre-commit)
[![Coverage Status](https://img.shields.io/coveralls/pre-commit/pre-commit.svg?branch=master)](https://coveralls.io/r/pre-commit/pre-commit)

## pre-commit

A framework for managing and maintaining multi-language pre-commit hooks.

## Introduction

At Yelp we rely heavily on pre-commit hooks to find and fix common
issues before changes are submitted for code review. We run our hooks before
every commit to automatically point out issues like missing semicolons,
whitespace problems, and testing statements in code. Automatically fixing these
issues before posting code reviews allows our code reviewer to pay attention to
architecture of a change and not worry about trivial errors.

As we created more libraries and projects we recognized that sharing our pre
commit hooks across projects is painful. We copied and pasted bash scripts from
project to project. We also had to manually change the hooks to work for
different project structures.

We believe that you should always use the best industry standard linters. Some
of the best linters are written in languages that you do not use in your
project or have installed on your machine. For example scss-lint is a linter
for SCSS written in ruby. If you're writing a project in node you should be able
to use scss-lint as a pre-commit hook without adding a Gemfile to your project
or understanding how to get scss-lint installed.

We built pre-commit to solve our hook issues. pre-commit is a multi-language
package manager for pre-commit hooks. You specify a list of hooks you want
and pre-commit manages the installation and execution of any hook written in any
language before every commit. pre-commit is specifically designed to not
require root access; if one of your developers doesn't have node installed but
modifies a javascript file, pre-commit automatically handles downloading and
building node to run jshint without root.

## Installation

Before you can run hooks, you need to have the pre-commit package manager
installed.

Using pip:

    pip install pre-commit

Non Administrative Installation:

    curl http://pre-commit.github.io/local-install.py | python

System Level Install:

    sudo curl https://bootstrap.pypa.io/get-pip.py | python - pre-commit

In a Python Project, add the following to your requirements.txt (or requirements-dev.txt):

    pre-commit


## Adding pre-commit Plugins To Your Project

Once you have pre-commit installed, adding pre-commit plugins to your project is
done with the `.pre-commit-config.yaml` configuration file.

Add a file called `.pre-commit-config.yaml` to the root of your project. The
pre-commit config file describes:

- `repo`, `sha` - where to get plugins (git repos).
- `id` - What plugins from the repo you want to use.
- `language_version` - (optional) Override the default language version for the hook.
  See Advanced Features: "Overriding Language Version"
- `files` - (optional) Override the default pattern for files to run on.
- `exclude` - (optional) File exclude pattern.
- `args` - (optional) additional parameters to pass to the hook.

For example:

    -   repo: git://github.com/pre-commit/pre-commit-hooks
        sha: 82344a4055f4e103afdc31e98a46de679fe55385
        hooks:
        -   id: trailing-whitespace

This configuration says to download the pre-commit-hooks project and run it's
trailing-whitespace hook.


## Usage

run `pre-commit install` to install pre-commit into your git hooks. pre-commit
will now run on every commit. Everytime you clone a project using pre-commit
running install should always be the first thing you do.

If you want to manually run all pre-commit hooks on a repository, run
`pre-commit run --all-files`. To run individual hooks use
`pre-commit run <hook_id>`.

The first time pre-commit runs on a file it will automatically download, install,
and run the hook. Note that running a hook for the first time may be slow.
For example: If the machine does not have node installed, pre-commit will download
and build a copy of node.


## Creating New Hooks

pre-commit currently supports hooks written in JavaScript (node), Python, Ruby
and system installed scripts. As long as your git repo is an installable package
(gem, npm, pypi, etc) or exposes a executable, it can be used with pre-commit.
Each git repo can support as many languages/hooks as you want.

An executable must satisfy the following things:

- Returncode of hook must be different between success / failures
  (Usually 0 for success, nonzero for failure)
- It must take filenames

A git repo containing pre-commit plugins must contain a hooks.yaml file that
tells pre-commit:

- `id` - The id of the hook - used in pre-commit-config.yaml
- `name` - The name of the hook - shown during hook execution
- `entry` - The entry point - The executable to run
- `files` - The pattern of files to run on.
- `language` - The language of the hook - tells pre-commit how to install the hook
- `description` - (optional) The description of the hook
- `language_version` - (optional) See advanced features "Overriding Language Version"
- `expected_return_value` - (optional) Defaults to 0

For example:

    -   id: trailing-whitespace
        name: Trim Trailing Whitespace
        description: This hook trims trailing whitespace.
        entry: trailing-whitespace-fixer
        language: python
        files: \.(js|rb|md|py|sh|txt|yaml|yml)$


## Popular Hooks

JSHint:

    -   repo: git://github.com/pre-commit/mirrors-jshint
        sha: 8e7fa9caad6f7b2aae8d2c7b64f457611416192b
        hooks:
        -   id: jshint

SCSS-Lint:

    -   repo: git://github.com/pre-commit/mirrors-scss-lint
        sha: d7266131da322d6d76a18d6a3659f21025d9ea11
        hooks:
        -   id: scss-lint

Ruby-Lint:

    -   repo: git://github.com/pre-commit/mirrors-ruby-lint
        sha: f4b537e0bf868fc6baefcb61288a12b35aac2157
        hooks:
        -   id: ruby-lint

Whitespace Fixers:

    -   repo: git://github.com/pre-commit/pre-commit-hooks
        sha: a751eb58f91d8fa70e8b87c9c95777c5a743a932
        hooks:
        -   id: trailing-whitespace
        -   id: end-of-file-fixer

flake8:

    -   repo: git://github.com/pre-commit/pre-commit-hooks
        sha: a751eb58f91d8fa70e8b87c9c95777c5a743a932
        hooks:
        -   id: flake8

pyflakes:

    -   repo: git://github.com/pre-commit/pre-commit-hooks
        sha: a751eb58f91d8fa70e8b87c9c95777c5a743a932
        hooks:
        -   id: pyflakes


## Advanced features

### Temporarily Disabling Hooks

Not all hooks are perfect so sometimes you may need to skip execution of
one or more hooks.  pre-commit solves this by querying a `SKIP` environment
variable.  The `SKIP` environment variable is a comma separated list of
hook ids.  This allows you to skip a single hook instead of `--no-verify`ing
the entire commit

    $ SKIP=flake8 git commit -m "foo"

### pre-commit During Commits

Running hooks on unstaged changes can lead to both false-positives and
false-negatives during committing.  pre-commit only runs on the staged
contents of files by temporarily saving the contents of your files at
commit time and stashing the unstaged changes while running hooks.

### pre-commit During Merges

The biggest gripe we've had in the past with pre-commit hooks was during
merge conflict resolution.  When working on very large projects a merge
often results in hundreds of committed files.  I shouldn't need to run
hooks on all of these files that I didn't even touch!  This often led
to running commit with `--no-verify` and allowed introduction of real
bugs that hooks could have caught through merge-conflict resolution.
pre-commit solves this by only running hooks on files that conflict or
were manually edited during conflict resolution.


### Passing Arguments to Hooks

Sometimes hooks require arguments to run correctly.  You can pass
static arguments by specifying the `args` property in your
`.pre-commit-config.yaml` as follows:

    -   repo: git://github.com/pre-commit/pre-commit-hooks
        sha: a751eb58f91d8fa70e8b87c9c95777c5a743a932
        hooks:
        -   id: flake8
            args: [--max-line-length=131]

This will pass `--max-line-length=131` to `flake8`


### Overriding Language Version

Sometimes you only want to run the hooks on a specific version of
the language.  For each language, they default to using the system
installed language (So for example if I'm running `python2.6` and a
hook specifies `python`, pre-commit will run the hook using `python2.6`).
Sometimes you don't want the default system installed version so you can
override this on a per-hook basis by setting the `language_version`.


    -   repo: git://github.com/pre-commit/mirrors-scss-lint
        sha: d7266131da322d6d76a18d6a3659f21025d9ea11
        hooks:
        -   id: scss-lint
            language_version: 1.9.3-p484

This tells pre-commit to use `1.9.3-p484` to run the `scss-lint` hook.

Valid values for specific languages are listed below:

- python: Whatever system installed python interpreters you have.
  The value of this argument is passed as the `-p` to `virtualenv`
- node: See https://github.com/ekalinin/nodeenv#advanced
- ruby: See https://github.com/sstephenson/ruby-build/tree/master/share/ruby-build


## Contributing

We're looking to grow the project and get more contributors especially
to support more languages/versions. We'd also like to get the hooks.yaml
files added to popular linters without maintaining forks / mirrors.

Feel free to submit Bug Reports, Pull Requests, and Feature Requests.

When submitting a pull request, please enable travis-ci for your fork.


## Contributors

- Anthony Sottile
- Ken Struys
