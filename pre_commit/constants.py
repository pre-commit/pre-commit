from __future__ import unicode_literals


CONFIG_FILE = '.pre-commit-config.yaml'

# In 0.12.0, the default file was changed to be namespaced
MANIFEST_FILE = '.pre-commit-hooks.yaml'
MANIFEST_FILE_LEGACY = 'hooks.yaml'

YAML_DUMP_KWARGS = {
    'default_flow_style': False,
    # Use unicode
    'encoding': None,
    'indent': 4,
}
