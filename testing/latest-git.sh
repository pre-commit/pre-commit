#!/usr/bin/env bash
# This is a script used in travis-ci to have latest git
set -ex
git clone git://github.com/git/git --depth 1 /tmp/git
pushd /tmp/git
make prefix=/tmp/git -j8 install
popd
