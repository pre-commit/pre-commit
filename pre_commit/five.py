from __future__ import unicode_literals

PY2 = str is bytes
PY3 = str is not bytes

if PY2:  # pragma: no cover (PY2 only)
    text = unicode  # flake8: noqa
    string_types = (text, bytes)

    def n(s):
        if isinstance(s, bytes):
            return s
        else:
            return s.encode('UTF-8')

    exec("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")
else:  # pragma: no cover (PY3 only)
    text = str
    string_types = (text,)

    def n(s):
        if isinstance(s, text):
            return s
        else:
            return s.decode('UTF-8')

    def reraise(tp, value, tb=None):
        if value is None:
            value = tp()
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


def to_text(s):
    return s if isinstance(s, text) else s.decode('UTF-8')


def to_bytes(s):
    return s if isinstance(s, bytes) else s.encode('UTF-8')
