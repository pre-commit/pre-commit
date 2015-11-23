from __future__ import unicode_literals

import os
import os.path
import shutil

import jsonschema
import pytest

from pre_commit.util import cmd_output
from pre_commit.util import cwd


TESTING_DIR = os.path.abspath(os.path.dirname(__file__))


def get_resource_path(path):
    return os.path.join(TESTING_DIR, 'resources', path)


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


def get_head_sha(dir):
    with cwd(dir):
        return cmd_output('git', 'rev-parse', 'HEAD')[1].strip()


def is_valid_according_to_schema(obj, schema):
    try:
        jsonschema.validate(obj, schema)
        return True
    except jsonschema.exceptions.ValidationError:
        return False


skipif_slowtests_false = pytest.mark.skipif(
    os.environ.get('slowtests') == 'false',
    reason='slowtests=false',
)

xfailif_windows_no_ruby = pytest.mark.xfail(
    os.name == 'nt',
    reason='Ruby support not yet implemented on windows.',
)

xfailif_windows_no_node = pytest.mark.xfail(
    os.name == 'nt',
    reason='Node support not yet implemented on windows.',
)


def platform_supports_pcre():
    output = cmd_output('grep', '-P', 'setup', 'setup.py', retcode=None)
    return output[0] == 0 and 'from setuptools import setup' in output[1]


xfailif_no_pcre_support = pytest.mark.xfail(
    not platform_supports_pcre(),
    reason='grep -P is not supported on this platform',
)

xfailif_no_symlink = pytest.mark.xfail(
    not hasattr(os, 'symlink'),
    reason='Symlink is not supported on this platform',
)
