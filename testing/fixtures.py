from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os.path

from aspy.yaml import ordered_dump

import pre_commit.constants as C
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.clientlib.validate_manifest import load_manifest
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.ordereddict import OrderedDict
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.util import copy_tree_to_path
from testing.util import get_head_sha
from testing.util import get_resource_path


def git_dir(tmpdir_factory):
    path = tmpdir_factory.get()
    with cwd(path):
        cmd_output('git', 'init')
    return path


def make_repo(tmpdir_factory, repo_source):
    path = git_dir(tmpdir_factory)
    copy_tree_to_path(get_resource_path(repo_source), path)
    with cwd(path):
        cmd_output('git', 'add', '.')
        cmd_output('git', 'commit', '-m', 'Add hooks')
    return path


def make_config_from_repo(repo_path, sha=None, hooks=None, check=True):
    manifest = load_manifest(os.path.join(repo_path, C.MANIFEST_FILE))
    config = OrderedDict((
        ('repo', repo_path),
        ('sha', sha or get_head_sha(repo_path)),
        (
            'hooks',
            hooks or [OrderedDict((('id', hook['id']),)) for hook in manifest],
        ),
    ))

    if check:
        wrapped_config = apply_defaults([config], CONFIG_JSON_SCHEMA)
        validate_config_extra(wrapped_config)
        return wrapped_config[0]
    else:
        return config


def write_config(directory, config):
    assert type(config) is OrderedDict
    with io.open(os.path.join(directory, C.CONFIG_FILE), 'w') as config_file:
        config_file.write(ordered_dump([config], **C.YAML_DUMP_KWARGS))


def add_config_to_repo(git_path, config):
    write_config(git_path, config)
    with cwd(git_path):
        cmd_output('git', 'add', C.CONFIG_FILE)
        cmd_output('git', 'commit', '-m', 'Add hooks config')
    return git_path


def make_consuming_repo(tmpdir_factory, repo_source):
    path = make_repo(tmpdir_factory, repo_source)
    config = make_config_from_repo(path)
    git_path = git_dir(tmpdir_factory)
    return add_config_to_repo(git_path, config)
