#!/usr/bin/env bash
# This is a script used in travis-ci to install swift
set -euxo pipefail

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "trusty" ]; then
    SWIFT_URL='https://swift.org/builds/swift-4.0.3-release/ubuntu1404/swift-4.0.3-RELEASE/swift-4.0.3-RELEASE-ubuntu14.04.tar.gz'
    SWIFT_HASH="dddb40ec4956e4f6a3f4532d859691d5d1ba8822f6e8b4ec6c452172dbede5ae"
else
    SWIFT_URL='https://swift.org/builds/swift-4.0.3-release/ubuntu1604/swift-4.0.3-RELEASE/swift-4.0.3-RELEASE-ubuntu16.04.tar.gz'
    SWIFT_HASH="9adf64cabc7c02ea2d08f150b449b05e46bd42d6e542bf742b3674f5c37f0dbf"
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
