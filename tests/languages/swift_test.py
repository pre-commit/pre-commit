from __future__ import annotations

import sys

import pytest

from pre_commit.languages import swift
from testing.language_helpers import run_language


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='swift is not supported on windows',
)
def test_swift_language(tmp_path):  # pragma: win32 no cover
    package_swift = '''\
// swift-tools-version:5.0
import PackageDescription

let package = Package(
    name: "swift_hooks_repo",
    targets: [.target(name: "swift_hooks_repo")]
)
'''
    tmp_path.joinpath('Package.swift').write_text(package_swift)
    src_dir = tmp_path.joinpath('Sources/swift_hooks_repo')
    src_dir.mkdir(parents=True)
    src_dir.joinpath('main.swift').write_text('print("Hello, world!")\n')

    expected = (0, b'Hello, world!\n')
    assert run_language(tmp_path, swift, 'swift_hooks_repo') == expected
