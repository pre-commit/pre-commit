#!/usr/bin/env bash

for f in $@; do
    echo modified > "$f"
    echo "Modified: $f!"
done
