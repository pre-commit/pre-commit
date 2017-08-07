#!/usr/bin/env bash
# This is a script used in travis-ci to install swift
set -ex

. /etc/lsb-release
if [ "$DISTRIB_CODENAME" = "trusty" ]; then
    SWIFT_URL='https://swift.org/builds/swift-3.1.1-release/ubuntu1404/swift-3.1.1-RELEASE/swift-3.1.1-RELEASE-ubuntu14.04.tar.gz'
else
    SWIFT_URL='https://swift.org/builds/swift-3.1.1-release/ubuntu1604/swift-3.1.1-RELEASE/swift-3.1.1-RELEASE-ubuntu16.04.tar.gz'
fi

mkdir -p /tmp/swift
pushd /tmp/swift
    wget "$SWIFT_URL" -O swift.tar.gz
    tar -xf swift.tar.gz --strip 1
popd
