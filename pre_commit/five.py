"""five: six, redux"""
# pylint:disable=invalid-name
PY2 = (str is bytes)
PY3 = (str is not bytes)

# provide a symettrical `text` type to `bytes`
if PY2:
    text = unicode  # flake8: noqa
else:
    text = str
