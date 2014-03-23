from __future__ import absolute_import

# This module serves only as a shim for OrderedDict

try:
    from collections import OrderedDict
except ImportError:
    from orderddict import OrderedDict

__all__ = (OrderedDict.__name__,)
