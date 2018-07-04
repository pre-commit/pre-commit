#!/usr/bin/env bash
# This is a script used in travis-ci to install swift
set -ex

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "trusty" ]; then
    SWIFT_TARBALL="swift-4.0.3-RELEASE-ubuntu14.04.tar.gz"
    SWIFT_HASH="dddb40ec4956e4f6a3f4532d859691d5d1ba8822f6e8b4ec6c452172dbede5ae"
    SWIFT_URL="https://swift.org/builds/swift-4.0.3-release/ubuntu1404/swift-4.0.3-RELEASE/$SWIFT_TARBALL"
else
    SWIFT_TARBALL="swift-4.0.3-RELEASE-ubuntu16.04.tar.gz"
    SWIFT_HASH="9adf64cabc7c02ea2d08f150b449b05e46bd42d6e542bf742b3674f5c37f0dbf"
    SWIFT_URL="https://swift.org/builds/swift-4.0.3-release/ubuntu1604/swift-4.0.3-RELEASE/$SWIFT_TARBALL"
fi

mkdir -p "$HOME"/.swift
pushd "$HOME"/.swift
    wget -N -c "$SWIFT_URL"
    echo "$SWIFT_HASH  $SWIFT_TARBALL" > hash.txt
    shasum -a 256 -c hash.txt
popd

mkdir -p /tmp/swift
pushd /tmp/swift
    tar -xf "$HOME"/.swift/"$SWIFT_TARBALL" --strip 1
popd
