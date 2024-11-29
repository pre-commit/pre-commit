from __future__ import annotations

import functools
import os
import re
from typing import Any

import yaml


def env_constructor(loader: yaml.Loader, node: yaml.ScalarNode) -> str:
    """Load !Env tag"""
    value = str(loader.construct_scalar(node))
    match = re.compile('.*?\\${(\\w+)}.*?').findall(value)
    if match:
        for key in match:
            value = value.replace(f'${{{key}}}', os.getenv(key, ''))
    return value


Loader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
Loader.add_constructor(tag='!Env', constructor=env_constructor)

yaml_compose = functools.partial(yaml.compose, Loader=Loader)
yaml_load = functools.partial(yaml.load, Loader=Loader)
Dumper = getattr(yaml, 'CSafeDumper', yaml.SafeDumper)


def yaml_dump(o: Any, **kwargs: Any) -> str:
    # when python/mypy#1484 is solved, this can be `functools.partial`
    return yaml.dump(
        o, Dumper=Dumper, default_flow_style=False, indent=4, sort_keys=False,
        **kwargs,
    )
