#!/usr/bin/env bash
set -euo pipefail

if [ "$OSTYPE" = msys ]; then
    URL='https://github.com/coursier/coursier/releases/download/v2.1.0-RC4/cs-x86_64-pc-win32.zip'
    SHA256='0d07386ff0f337e3e6264f7dde29d137dda6eaa2385f29741435e0b93ccdb49d'
    TARGET='/tmp/coursier/cs.zip'

    unpack() {
        unzip "$TARGET" -d /tmp/coursier
        mv /tmp/coursier/cs-*.exe /tmp/coursier/cs.exe
        cygpath -w /tmp/coursier >> "$GITHUB_PATH"
    }
else
    URL='https://github.com/coursier/coursier/releases/download/v2.1.0-RC4/cs-x86_64-pc-linux.gz'
    SHA256='176e92e08ab292531aa0c4993dbc9f2c99dec79578752f3b9285f54f306db572'
    TARGET=/tmp/coursier/cs.gz

    unpack() {
        gunzip "$TARGET"
        chmod +x /tmp/coursier/cs
        echo /tmp/coursier >> "$GITHUB_PATH"
    }
fi

mkdir -p /tmp/coursier
curl --location --silent --output "$TARGET" "$URL"
echo "$SHA256 $TARGET" | sha256sum --check
unpack
