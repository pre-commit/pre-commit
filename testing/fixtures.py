import contextlib
import os.path
import shutil

from aspy.yaml import ordered_dump
from aspy.yaml import ordered_load
from cfgv import apply_defaults
from cfgv import validate

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import CONFIG_SCHEMA
from pre_commit.clientlib import load_manifest
from pre_commit.util import cmd_output
from testing.util import get_resource_path
from testing.util import git_commit


def copy_tree_to_path(src_dir, dest_dir):
    """Copies all of the things inside src_dir to an already existing dest_dir.

    This looks eerily similar to shutil.copytree, but copytree has no option
    for not creating dest_dir.
    """
    names = os.listdir(src_dir)

    for name in names:
        srcname = os.path.join(src_dir, name)
        destname = os.path.join(dest_dir, name)

        if os.path.isdir(srcname):
            shutil.copytree(srcname, destname)
        else:
            shutil.copy(srcname, destname)


def git_dir(tempdir_factory):
    path = tempdir_factory.get()
    cmd_output('git', 'init', path)
    return path


def make_repo(tempdir_factory, repo_source):
    path = git_dir(tempdir_factory)
    copy_tree_to_path(get_resource_path(repo_source), path)
    cmd_output('git', 'add', '.', cwd=path)
    git_commit(msg=make_repo.__name__, cwd=path)
    return path


@contextlib.contextmanager
def modify_manifest(path, commit=True):
    """Modify the manifest yielded by this context to write to
    .pre-commit-hooks.yaml.
    """
    manifest_path = os.path.join(path, C.MANIFEST_FILE)
    with open(manifest_path) as f:
        manifest = ordered_load(f.read())
    yield manifest
    with open(manifest_path, 'w') as manifest_file:
        manifest_file.write(ordered_dump(manifest, **C.YAML_DUMP_KWARGS))
    if commit:
        git_commit(msg=modify_manifest.__name__, cwd=path)


@contextlib.contextmanager
def modify_config(path='.', commit=True):
    """Modify the config yielded by this context to write to
    .pre-commit-config.yaml
    """
    config_path = os.path.join(path, C.CONFIG_FILE)
    with open(config_path) as f:
        config = ordered_load(f.read())
    yield config
    with open(config_path, 'w', encoding='UTF-8') as config_file:
        config_file.write(ordered_dump(config, **C.YAML_DUMP_KWARGS))
    if commit:
        git_commit(msg=modify_config.__name__, cwd=path)


def sample_local_config():
    return {
        'repo': 'local',
        'hooks': [{
            'id': 'do_not_commit',
            'name': 'Block if "DO NOT COMMIT" is found',
            'entry': 'DO NOT COMMIT',
            'language': 'pygrep',
        }],
    }


def sample_meta_config():
    return {'repo': 'meta', 'hooks': [{'id': 'check-useless-excludes'}]}


def make_config_from_repo(repo_path, rev=None, hooks=None, check=True):
    manifest = load_manifest(os.path.join(repo_path, C.MANIFEST_FILE))
    config = {
        'repo': f'file://{repo_path}',
        'rev': rev or git.head_rev(repo_path),
        'hooks': hooks or [{'id': hook['id']} for hook in manifest],
    }

    if check:
        wrapped = validate({'repos': [config]}, CONFIG_SCHEMA)
        wrapped = apply_defaults(wrapped, CONFIG_SCHEMA)
        config, = wrapped['repos']
        return config
    else:
        return config


def read_config(directory, config_file=C.CONFIG_FILE):
    config_path = os.path.join(directory, config_file)
    with open(config_path) as f:
        config = ordered_load(f.read())
    return config


def write_config(directory, config, config_file=C.CONFIG_FILE):
    if type(config) is not list and 'repos' not in config:
        assert isinstance(config, dict), config
        config = {'repos': [config]}
    with open(os.path.join(directory, config_file), 'w') as outfile:
        outfile.write(ordered_dump(config, **C.YAML_DUMP_KWARGS))


def add_config_to_repo(git_path, config, config_file=C.CONFIG_FILE):
    write_config(git_path, config, config_file=config_file)
    cmd_output('git', 'add', config_file, cwd=git_path)
    git_commit(msg=add_config_to_repo.__name__, cwd=git_path)
    return git_path


def remove_config_from_repo(git_path, config_file=C.CONFIG_FILE):
    cmd_output('git', 'rm', config_file, cwd=git_path)
    git_commit(msg=remove_config_from_repo.__name__, cwd=git_path)
    return git_path


def make_consuming_repo(tempdir_factory, repo_source):
    path = make_repo(tempdir_factory, repo_source)
    config = make_config_from_repo(path)
    git_path = git_dir(tempdir_factory)
    return add_config_to_repo(git_path, config)
