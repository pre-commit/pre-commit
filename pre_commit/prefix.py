from __future__ import unicode_literals

import os.path


class Prefix(object):
    def __init__(self, prefix_dir):
        self.prefix_dir = prefix_dir.rstrip(os.sep) + os.sep

    def path(self, *parts):
        path = os.path.join(self.prefix_dir, *parts)
        return os.path.normpath(path)

    def exists(self, *parts):
        return os.path.exists(self.path(*parts))

    def star(self, end):
        return tuple(
            path for path in os.listdir(self.prefix_dir) if path.endswith(end)
        )
