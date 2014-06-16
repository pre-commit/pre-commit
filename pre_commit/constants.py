from __future__ import unicode_literals


CONFIG_FILE = '.pre-commit-config.yaml'

MANIFEST_FILE = 'hooks.yaml'

YAML_DUMP_KWARGS = {
    'default_flow_style': False,
    # Use unicode
    'encoding': None,
    'indent': 4,
}
