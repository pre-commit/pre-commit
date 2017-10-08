from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import os.path

from aspy.yaml import ordered_dump

import pre_commit.constants as C
from pre_commit import git
from pre_commit import output
from pre_commit.commands.run import run
from pre_commit.manifest import Manifest
from pre_commit.runner import Runner
from pre_commit.store import Store
from pre_commit.util import tmpdir


def try_repo(args):
    ref = args.ref or git.head_sha(args.repo)

    with tmpdir() as tempdir:
        if args.hook:
            hooks = [{'id': args.hook}]
        else:
            manifest = Manifest(Store(tempdir).clone(args.repo, ref))
            hooks = [{'id': hook_id} for hook_id in sorted(manifest.hooks)]

        items = (('repo', args.repo), ('sha', ref), ('hooks', hooks))
        config = {'repos': [collections.OrderedDict(items)]}
        config_s = ordered_dump(config, **C.YAML_DUMP_KWARGS)

        config_filename = os.path.join(tempdir, C.CONFIG_FILE)
        with open(config_filename, 'w') as cfg:
            cfg.write(config_s)

        output.write_line('=' * 79)
        output.write_line('Using config:')
        output.write_line('=' * 79)
        output.write(config_s)
        output.write_line('=' * 79)

        runner = Runner('.', config_filename, store_dir=tempdir)
        return run(runner, args)
