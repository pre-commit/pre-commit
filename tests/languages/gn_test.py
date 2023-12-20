from __future__ import annotations

import re

from pre_commit.languages import gn
from testing.language_helpers import run_language


def test_gn_format(tmp_path):
    # Create a GN file with content that needs formatting
    gn_file_content = """\
source_set("hello_world") {
    sources = [ "hello_world.cc", ]
}
"""
    gn_file = tmp_path.joinpath('test.gn')
    gn_file.write_text(gn_file_content)

    # Run gn format on the created file
    ret, out = run_language(tmp_path, gn, f'gn format {gn_file}')

    # Read the formatted file
    formatted_content = gn_file.read_text()

    assert ret == 0
    assert gn_file_content != formatted_content


def test_gn_version(tmp_path):
    ret, out = run_language(
        tmp_path,
        gn,
        'gn --version',
    )
    assert ret == 0
    version_regex = re.compile(rb'\d+ \([a-f0-9]+\)\n')
    assert version_regex.search(out) is not None
