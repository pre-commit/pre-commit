import collections


def auto_namedtuple(classname='auto_namedtuple', **kwargs):
    """Returns an automatic namedtuple object.

    Args:
        classname - The class name for the returned object.
        **kwargs - Properties to give the returned object.
    """
    return (collections.namedtuple(classname, kwargs.keys())(**kwargs))
