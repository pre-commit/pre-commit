from __future__ import annotations

import importlib.metadata

CONFIG_FILE = '.pre-commit-config.yaml'
MANIFEST_FILE = '.pre-commit-hooks.yaml'

# Bump when modifying `empty_template`
LOCAL_REPO_VERSION = '1'

VERSION = importlib.metadata.version('pre_commit')

# `manual` is not invoked by any installed git hook.  See #719
STAGES = (
    'commit', 'merge-commit', 'prepare-commit-msg', 'commit-msg',
    'post-commit', 'manual', 'post-checkout', 'push', 'post-merge',
    'post-rewrite',
)

HOOK_TYPES = (
    'pre-commit', 'pre-merge-commit', 'pre-push', 'prepare-commit-msg',
    'commit-msg', 'post-commit', 'post-checkout', 'post-merge',
    'post-rewrite',
)

DEFAULT = 'default'
