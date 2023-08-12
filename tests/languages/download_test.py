from __future__ import annotations

import platform
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from threading import Thread
from typing import Collection
from typing import Iterator

import py.path
from pytest import fixture

import pre_commit.constants as C
from pre_commit.languages import download
from pre_commit.languages.download import ChecksumMismatchError
from pre_commit.languages.download import SRI
from pre_commit.languages.download import URI
from pre_commit.prefix import Prefix


@dataclass(frozen=True)
class Script:
    content: bytes
    integrity: SRI


@fixture
def shell() -> Script:
    content = b'#!/bin/sh\necho hello\nexit 123'
    integrity = SRI('sha256-oRJkj6Cr8nWIivZ9d3W+rVZt/aSW1l9YtxSVh+GtIHM=')
    return Script(content, integrity)


@fixture
def batch() -> Script:
    content = b'@echo off\necho hello\nexit 123'
    integrity = SRI('sha256-L63Nefq+fKVIm24IKqlcqbJmc1rrJD3dKhIvutFK+IA=')
    return Script(content, integrity)


@fixture
def script(shell: Script, batch: Script) -> Script:
    if platform.system() == 'Windows':
        return batch
    else:
        return shell


@dataclass(frozen=True)
class Server:
    uri: URI
    script: Script


@fixture
def server(script: Script) -> Iterator[Server]:
    class HTTPRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(script.content)
    httpd = HTTPServer(('localhost', 5555), HTTPRequestHandler)
    thread = Thread(target=httpd.serve_forever, name='HTTP Server')
    thread.start()
    host, port = httpd.server_address
    uri = URI(f'http://{str(host)}:{str(port)}')
    try:
        yield Server(uri, fixture)
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(1)
        assert not thread.is_alive()


@dataclass(frozen=True)
class Fixture:
    server: Server
    dependencies: Collection[str]


@fixture
def healthy(server: Server, shell: Script, batch: Script) -> Fixture:
    dependencies = (
        f"""linux/amd64
{shell.integrity}
{server.uri}
test.bat""",
        f"""windows/amd64
{batch.integrity}
{server.uri}
test.bat""",
    )
    return Fixture(server, dependencies)


@fixture
def unhealthy(server: Server, shell: Script, batch: Script) -> Fixture:
    dependencies = (
        f"""linux/amd64
{batch.integrity}
{server.uri}
test.bat""",
        f"""windows/amd64
{shell.integrity}
{server.uri}
test.bat""",
    )
    return Fixture(server, dependencies)


@fixture
def prefix(tmpdir: py.path) -> Iterator[Prefix]:
    with tmpdir.as_cwd():
        directory = tmpdir.join('prefix').ensure_dir()
        prefix = Prefix(str(directory))
        yield prefix


def test_download_healthy(prefix: Prefix, healthy: Fixture) -> None:
    """Do a download test with healthy SRI checksum"""
    download.install_environment(prefix, C.DEFAULT, healthy.dependencies)
    assert download.health_check(prefix, C.DEFAULT) is None


def test_download_unhealthy(prefix: Prefix, unhealthy: Fixture) -> None:
    """Do a download test with unhealthy SRI checksum"""
    try:
        download.install_environment(prefix, C.DEFAULT, unhealthy.dependencies)
    except ChecksumMismatchError:
        pass
