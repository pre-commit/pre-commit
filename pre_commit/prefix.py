from __future__ import unicode_literals

import collections
import os.path


class Prefix(collections.namedtuple('Prefix', ('prefix_dir',))):
    __slots__ = ()

    def path(self, *parts):
        return os.path.normpath(os.path.join(self.prefix_dir, *parts))

    def exists(self, *parts):
        return os.path.exists(self.path(*parts))

    def star(self, end):
        paths = os.listdir(self.prefix_dir)
        return tuple(path for path in paths if path.endswith(end))
