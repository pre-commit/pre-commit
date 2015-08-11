"""List of known filename to file type mappings.

The list consists of tuples of (filename regex, list of types).

Most of these are extensions (e.g. *.py -> python), but some just use the
filename (e.g. Makefile -> make).
"""
KNOWN_EXTENSIONS = [
    (r'\.js$', ['javascript']),
    (r'\.json$', ['json']),
    (r'\.py$', ['python']),
    (r'\.rb$', ['ruby']),
    (r'\.sh$', ['shell']),
    (r'\.e?ya?ml$', ['yaml']),
    (r'\.pp$', ['puppet']),
    (r'\.erb$', ['erb']),
    (r'\.json$', ['json']),
    (r'\.xml$', ['xml']),
    (r'\.c$', ['c']),
    (r'^Makefile$', ['make']),
    (r'\.mk$', ['make']),
    (r'\.png$', ['png']),
    (r'\.gif$', ['gif']),
    (r'\.svg$', ['svg']),
    (r'\.css$', ['css']),
    (r'\.html?$', ['html']),
    (r'\.php\d?$', ['php']),
]
