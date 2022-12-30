#!/usr/bin/env bash
# This is a script used in CI to install swift
set -euo pipefail

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "jammy" ]; then
    SWIFT_URL='https://download.swift.org/swift-5.7.1-release/ubuntu2204/swift-5.7.1-RELEASE/swift-5.7.1-RELEASE-ubuntu22.04.tar.gz'
    SWIFT_HASH='7f60291f5088d3e77b0c2364beaabd29616ee7b37260b7b06bdbeb891a7fe161'
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

echo '/tmp/swift/usr/bin' >> "$GITHUB_PATH"
