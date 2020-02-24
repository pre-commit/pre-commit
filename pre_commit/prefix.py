import os.path
from typing import NamedTuple
from typing import Tuple


class Prefix(NamedTuple):
    prefix_dir: str


def Prefix_path(self, *parts: str) -> str:
    return os.path.normpath(os.path.join(self.prefix_dir, *parts))


def Prefix_exists(self, *parts: str) -> bool:
    return os.path.exists(self.path(*parts))


def Prefix_star(self, end: str) -> Tuple[str, ...]:
    paths = os.listdir(self.prefix_dir)
    return tuple(path for path in paths if path.endswith(end))


# python 3.6.0 does not support methods on `typing.NamedTuple`
Prefix.path = Prefix_path
Prefix.exists = Prefix_exists
Prefix.star = Prefix_star
