from __future__ import absolute_import
from __future__ import unicode_literals

import contextlib
import io
import os.path
from collections import OrderedDict

from aspy.yaml import ordered_dump
from aspy.yaml import ordered_load
from cfgv import apply_defaults
from cfgv import validate

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import CONFIG_SCHEMA
from pre_commit.clientlib import load_manifest
from pre_commit.util import cmd_output
from pre_commit.util import copy_tree_to_path
from testing.util import get_resource_path


def git_dir(tempdir_factory):
    path = tempdir_factory.get()
    cmd_output('git', 'init', path)
    return path


def make_repo(tempdir_factory, repo_source):
    path = git_dir(tempdir_factory)
    copy_tree_to_path(get_resource_path(repo_source), path)
    cmd_output('git', 'add', '.', cwd=path)
    cmd_output('git', 'commit', '-m', 'Add hooks', cwd=path)
    return path


@contextlib.contextmanager
def modify_manifest(path):
    """Modify the manifest yielded by this context to write to
    .pre-commit-hooks.yaml.
    """
    manifest_path = os.path.join(path, C.MANIFEST_FILE)
    with io.open(manifest_path) as f:
        manifest = ordered_load(f.read())
    yield manifest
    with io.open(manifest_path, 'w') as manifest_file:
        manifest_file.write(ordered_dump(manifest, **C.YAML_DUMP_KWARGS))
    cmd_output(
        'git', 'commit', '-am', 'update {}'.format(C.MANIFEST_FILE), cwd=path,
    )


@contextlib.contextmanager
def modify_config(path='.', commit=True):
    """Modify the config yielded by this context to write to
    .pre-commit-config.yaml
    """
    config_path = os.path.join(path, C.CONFIG_FILE)
    with io.open(config_path) as f:
        config = ordered_load(f.read())
    yield config
    with io.open(config_path, 'w', encoding='UTF-8') as config_file:
        config_file.write(ordered_dump(config, **C.YAML_DUMP_KWARGS))
    if commit:
        cmd_output('git', 'commit', '-am', 'update config', cwd=path)


def config_with_local_hooks():
    return OrderedDict((
        ('repo', 'local'),
        (
            'hooks', [OrderedDict((
                ('id', 'do_not_commit'),
                ('name', 'Block if "DO NOT COMMIT" is found'),
                ('entry', 'DO NOT COMMIT'),
                ('language', 'pygrep'),
                ('files', '^(.*)$'),
            ))],
        ),
    ))


def make_config_from_repo(repo_path, rev=None, hooks=None, check=True):
    manifest = load_manifest(os.path.join(repo_path, C.MANIFEST_FILE))
    config = OrderedDict((
        ('repo', 'file://{}'.format(repo_path)),
        ('rev', rev or git.head_rev(repo_path)),
        (
            'hooks',
            hooks or [OrderedDict((('id', hook['id']),)) for hook in manifest],
        ),
    ))

    if check:
        wrapped = validate({'repos': [config]}, CONFIG_SCHEMA)
        wrapped = apply_defaults(wrapped, CONFIG_SCHEMA)
        config, = wrapped['repos']
        return config
    else:
        return config


def read_config(directory, config_file=C.CONFIG_FILE):
    config_path = os.path.join(directory, config_file)
    with io.open(config_path) as f:
        config = ordered_load(f.read())
    return config


def write_config(directory, config, config_file=C.CONFIG_FILE):
    if type(config) is not list and 'repos' not in config:
        assert type(config) is OrderedDict
        config = {'repos': [config]}
    with io.open(os.path.join(directory, config_file), 'w') as outfile:
        outfile.write(ordered_dump(config, **C.YAML_DUMP_KWARGS))


def add_config_to_repo(git_path, config, config_file=C.CONFIG_FILE):
    write_config(git_path, config, config_file=config_file)
    cmd_output('git', 'add', config_file, cwd=git_path)
    cmd_output('git', 'commit', '-m', 'Add hooks config', cwd=git_path)
    return git_path


def remove_config_from_repo(git_path, config_file=C.CONFIG_FILE):
    cmd_output('git', 'rm', config_file, cwd=git_path)
    cmd_output('git', 'commit', '-m', 'Remove hooks config', cwd=git_path)
    return git_path


def make_consuming_repo(tempdir_factory, repo_source):
    path = make_repo(tempdir_factory, repo_source)
    config = make_config_from_repo(path)
    git_path = git_dir(tempdir_factory)
    return add_config_to_repo(git_path, config)
