#!/usr/bin/env bash
# This is a script used in CI to install swift
set -euo pipefail

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "bionic" ]; then
    SWIFT_URL='https://swift.org/builds/swift-5.1.3-release/ubuntu1804/swift-5.1.3-RELEASE/swift-5.1.3-RELEASE-ubuntu18.04.tar.gz'
    SWIFT_HASH='ac82ccd773fe3d586fc340814e31e120da1ff695c6a712f6634e9cc720769610'
else
    echo "unknown dist: ${DISTRIB_CODENAME}" 1>&2
    exit 1
fi

check() {
    echo "$SWIFT_HASH  $TGZ" | sha256sum --check
}

TGZ="$HOME/.swift/swift.tar.gz"
mkdir -p "$(dirname "$TGZ")"
if ! check >& /dev/null; then
    rm -f "$TGZ"
    curl --location --silent --output "$TGZ" "$SWIFT_URL"
    check
fi

mkdir -p /tmp/swift
tar -xf "$TGZ" --strip 1 --directory /tmp/swift

echo '##vso[task.prependpath]/tmp/swift/usr/bin'
