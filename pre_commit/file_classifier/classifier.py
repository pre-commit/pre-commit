# encoding: utf-8
import io
import re
import string
from itertools import chain
from os.path import basename

from pre_commit.file_classifier.extensions import KNOWN_EXTENSIONS
from pre_commit.file_classifier.interpreters import KNOWN_INTERPRETERS
from pre_commit.git import GIT_MODE_EXECUTABLE
from pre_commit.git import GIT_MODE_FILE
from pre_commit.git import GIT_MODE_SUBMODULE
from pre_commit.git import GIT_MODE_SYMLINK


def classify(path, mode):
    """Return a set of tags for a file.

    :param path: path to the file
    :param mode: Git mode of the file
    :return: set of tags
    """
    tags = set()

    if mode in (GIT_MODE_FILE, GIT_MODE_EXECUTABLE):
        tags.add('file')

        types = _guess_types_from_extension(path)
        if types:
            tags.update(types)

        if _file_is_binary(path):
            tags.add('binary')
        else:
            tags.add('text')
            if not types:
                # only check the shebang if we couldn't guess by extension;
                # it's much slower
                tags.update(_guess_types_from_shebang(path))

        if mode == GIT_MODE_EXECUTABLE:
            tags.add('executable')
        else:
            tags.add('nonexecutable')

    elif mode == GIT_MODE_SYMLINK:
        tags.add('symlink')
    elif mode == GIT_MODE_SUBMODULE:
        tags.add('submodule')
    else:
        raise ValueError('Unknown git object mode: {}'.format(mode))

    return tags


def _guess_types_from_extension(path):
    """Guess types for a file based on extension.

    An extension could map to multiple file types, in which case we return the
    concatenation of types.
    """
    filename = basename(path)
    return list(chain.from_iterable(
        types for regex, types in KNOWN_EXTENSIONS
        if re.search(regex, filename)
    ))


def _guess_types_from_shebang(path):
    """Guess types for a text file based on shebang.

    A shebang could map to multiple file types, in which case we return the
    concatenation of types.
    """
    interpreter = _read_interpreter_from_shebang(path)
    if interpreter:
        return chain.from_iterable(
            types for regex, types in KNOWN_INTERPRETERS
            if re.match(regex, interpreter)
        )
    else:
        return []


def _read_interpreter_from_shebang(path):
    """Read an interpreter from a file's shebang.

    The first line of a script is guaranteed to be ASCII, so we read ASCII
    until we hit a newline (at which point we check if we read a valid shebang)
    or a non-ASCII character (at which point we bail).

    :param path: path to text file
    :return: interpreter, or None if no shebang could be read
    """
    MAX_SHEBANG_LENGTH = 128  # Linux kernel limit on shebangs

    with io.open(path, 'rb') as f:
        bytes_read = f.read(MAX_SHEBANG_LENGTH)

    chars_read = ''
    for i in range(MAX_SHEBANG_LENGTH):
        try:
            char = bytes_read[i:i + 1].decode('ascii')
            if char not in string.printable:
                return None
        except UnicodeDecodeError:
            return None  # no valid shebang

        if char != '\n':
            chars_read += char
        else:
            break

    if chars_read.startswith('#!'):
        words = chars_read[2:].strip().split()
        if not words or not words[0]:
            return None

        # take the first word of the shebang as the interpreter, unless that
        # word is something like /usr/bin/env
        if words[0].endswith('/env') and len(words) == 2:
            interpreter = words[1]
        else:
            interpreter = words[0]

        return interpreter.split('/')[-1]


def _file_is_binary(path):
    """Return whether the file seems to be binary.

    This is roughly based on libmagic's binary/text detection:
    https://github.com/file/file/blob/master/src/encoding.c#L203-L228
    """
    text_chars = (
        bytearray([7, 8, 9, 10, 12, 13, 27]) +
        bytearray(range(0x20, 0x7F)) +
        bytearray(range(0x80, 0X100))
    )
    with io.open(path, 'rb') as f:
        b = f.read(1024)  # only read first KB
    return bool(b.translate(None, text_chars))
