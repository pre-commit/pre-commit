def to_text(s):
    return s if isinstance(s, str) else s.decode('UTF-8')


def to_bytes(s):
    return s if isinstance(s, bytes) else s.encode('UTF-8')


n = to_text
