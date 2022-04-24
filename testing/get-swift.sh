#!/usr/bin/env bash
# This is a script used in CI to install swift
set -euo pipefail

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "focal" ]; then
    SWIFT_URL='https://download.swift.org/swift-5.6.1-release/ubuntu2004/swift-5.6.1-RELEASE/swift-5.6.1-RELEASE-ubuntu20.04.tar.gz'
    SWIFT_HASH='2b4f22d4a8b59fe8e050f0b7f020f8d8f12553cbda56709b2340a4a3bb90cfea'
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
