
CONFIG_FILE = '.pre-commit-config.yaml'

HOOKS_WORKSPACE = '.pre-commit-files'

MANIFEST_FILE = 'hooks.yaml'

SUPPORTED_LANGUAGES = set([
    'python',
    'ruby',
    'node',
])


YAML_DUMP_KWARGS = {
    'default_flow_style': False,
    'indent': 4,
}
