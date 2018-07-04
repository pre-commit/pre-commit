#!/usr/bin/env bash
# This is a script used in travis-ci to install swift
set -ex

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "trusty" ]; then
    SWIFT_TARBALL="swift-4.0.3-RELEASE-ubuntu14.04.tar.gz"
    SWIFT_URL="https://swift.org/builds/swift-4.0.3-release/ubuntu1404/swift-4.0.3-RELEASE/$SWIFT_TARBALL"
else
    SWIFT_TARBALL="swift-4.0.3-RELEASE-ubuntu16.04.tar.gz"
    SWIFT_URL="https://swift.org/builds/swift-4.0.3-release/ubuntu1604/swift-4.0.3-RELEASE/$SWIFT_TARBALL"
fi

pushd "$HOME"/.swift
    wget -N -c "$SWIFT_URL"
popd

mkdir -p /tmp/swift
pushd /tmp/swift
    tar -xf "$HOME"/.swift/"$SWIFT_TARBALL" --strip 1
popd
