from __future__ import absolute_import
from __future__ import unicode_literals

import importlib_metadata  # TODO: importlib.metadata py38?

CONFIG_FILE = '.pre-commit-config.yaml'
MANIFEST_FILE = '.pre-commit-hooks.yaml'

YAML_DUMP_KWARGS = {
    'default_flow_style': False,
    # Use unicode
    'encoding': None,
    'indent': 4,
}

# Bump when installation changes in a backwards / forwards incompatible way
INSTALLED_STATE_VERSION = '1'
# Bump when modifying `empty_template`
LOCAL_REPO_VERSION = '1'

VERSION = importlib_metadata.version('pre_commit')

# `manual` is not invoked by any installed git hook.  See #719
STAGES = ('commit', 'prepare-commit-msg', 'commit-msg', 'manual', 'push')

DEFAULT = 'default'
