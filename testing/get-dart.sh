#!/usr/bin/env bash
set -euo pipefail

VERSION=2.13.4

if [ "$OSTYPE" = msys ]; then
    URL="https://storage.googleapis.com/dart-archive/channels/stable/release/${VERSION}/sdk/dartsdk-windows-x64-release.zip"
    echo "##vso[task.prependpath]$(cygpath -w /tmp/dart-sdk/bin)"
else
    URL="https://storage.googleapis.com/dart-archive/channels/stable/release/${VERSION}/sdk/dartsdk-linux-x64-release.zip"
    echo '##vso[task.prependpath]/tmp/dart-sdk/bin'
fi

curl --silent --location --output /tmp/dart.zip "$URL"

unzip -q -d /tmp /tmp/dart.zip
rm /tmp/dart.zip
