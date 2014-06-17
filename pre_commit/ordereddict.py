from __future__ import absolute_import
from __future__ import unicode_literals

try:
    from collections import OrderedDict  # noqa
except ImportError:  # pragma: no cover (PY26)
    from ordereddict import OrderedDict  # noqa
