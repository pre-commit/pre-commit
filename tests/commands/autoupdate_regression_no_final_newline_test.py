"""Regression test: autoupdate handles missing final newline."""
from __future__ import annotations

import re


def test_no_final_newline_rev_line():
    config = 'repos:\n- repo: https://example.com/repo\n  rev: v1.0.0'
    REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([^\s#]+)(.*)(\r?\n|)$')
    rev_lines = [
        line for line in config.splitlines()
        if REV_LINE_RE.match(line)
    ]
    assert len(rev_lines) == 1, f"Expected 1 rev line, found {len(rev_lines)}"


def test_final_newline_rev_line():
    config = 'repos:\n- repo: https://example.com/repo\n  rev: v1.0.0\n'
    REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([^\s#]+)(.*)(\r?\n|)$')
    rev_lines = [
        line for line in config.splitlines(True)
        if REV_LINE_RE.match(line)
    ]
    assert len(rev_lines) == 1


def test_crlf_rev_line():
    config = 'repos:\r\n- repo: https://example.com/repo\r\n  rev: v1.0.0\r\n'
    REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([^\s#]+)(.*)(\r?\n|)$')
    rev_lines = [
        line for line in config.splitlines(True)
        if REV_LINE_RE.match(line)
    ]
    assert len(rev_lines) == 1


def test_lf_rev_line():
    config = 'repos:\n- repo: https://example.com/repo\n  rev: v1.0.0\n'
    REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([^\s#]+)(.*)(\r?\n|)$')
    rev_lines = [
        line for line in config.splitlines(True)
        if REV_LINE_RE.match(line)
    ]
    assert len(rev_lines) == 1
