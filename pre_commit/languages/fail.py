from __future__ import unicode_literals

from pre_commit.languages import helpers


ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(prefix, hook, file_args):
    out = hook['entry'].encode('UTF-8') + b'\n\n'
    out += b'\n'.join(f.encode('UTF-8') for f in file_args) + b'\n'
    return 1, out, b''
