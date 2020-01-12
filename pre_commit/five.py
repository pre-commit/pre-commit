from typing import Union


def to_text(s: Union[str, bytes]) -> str:
    return s if isinstance(s, str) else s.decode()


def to_bytes(s: Union[str, bytes]) -> bytes:
    return s if isinstance(s, bytes) else s.encode()


n = to_text
