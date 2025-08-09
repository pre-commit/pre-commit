#!/usr/bin/env bash
set -euo pipefail

VERSION=2.19.6

if [ "$OSTYPE" = msys ]; then
    URL="https://storage.googleapis.com/dart-archive/channels/stable/release/${VERSION}/sdk/dartsdk-windows-x64-release.zip"
    cygpath -w /tmp/dart-sdk/bin >> "$GITHUB_PATH"
else
    URL="https://storage.googleapis.com/dart-archive/channels/stable/release/${VERSION}/sdk/dartsdk-linux-x64-release.zip"
    echo '/tmp/dart-sdk/bin' >> "$GITHUB_PATH"
fi

curl --silent --location --output /tmp/dart.zip "$URL"

unzip -q -d /tmp /tmp/dart.zip
rm /tmp/dart.zip
