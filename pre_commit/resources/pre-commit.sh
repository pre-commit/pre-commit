#!/usr/bin/env bash

which pre-commit > /dev/null
if [ $? -ne 0 ]; then
    echo '`pre-commit` not found.  Did you forget to activate your virtualenv?'
    exit 1
fi

pre-commit
