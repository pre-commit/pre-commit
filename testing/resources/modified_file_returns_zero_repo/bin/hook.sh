#!/usr/bin/env bash

for f in "$@"; do
    # Non UTF-8 bytes
    echo -e '\x01\x97' > "$f"
    echo "Modified: $f!"
done
