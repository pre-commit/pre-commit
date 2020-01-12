#!/usr/bin/env bash
# Intentionally write mixed encoding to the output.  This should not crash
# pre-commit and should write bytes to the output.
# '☃'.encode() + '²'.encode('latin1')
echo -e '\xe2\x98\x83\xb2'
# exit 1 to trigger printing
exit 1
