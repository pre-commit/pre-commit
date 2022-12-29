import io
import os
import platform
import re
import sys
import sysconfig
from tarfile import TarFile
from tarfile import TarInfo
from typing import Generator
from urllib.parse import urljoin
from urllib.request import urlopen
from zipfile import ZipFile

import pre_commit.constants as C

ARCHITECTURES = {
    'x86': 'x86',  # Windows Vista 32
    'i686': 'x86',
    'x86_64': 'x64',  # Linux Ubuntu 64
    'amd64': 'x64',  # FreeBSD 64bits
    'AMD64': 'x64',  # Windows Server 2012 R2 (x64)
    'armv6l': 'armv6l',  # arm
    'armv7l': 'armv7l',
    'armv8l': 'armv7l',
    'aarch64': 'arm64',
    'arm64': 'arm64',
    'arm64/v8': 'arm64',
    'armv8': 'arm64',
    'armv8.4': 'arm64',
    'ppc64le': 'ppc64le',  # Power PC
    's390x': 's390x',  # IBM S390x
}

NIX_NODE_SUBDIRS = re.compile(r'node[^/]+/(bin|lib|include|share)')
WINDOWS_NODE_SUBDIRS = re.compile(r'node[^/]+(np|node)')


def install_node(envdir: str, language_version: str) -> str:
    windows = sys.platform in ('cygwin', 'win32')

    if sysconfig.get_config_var('HOST_GNU_TYPE') == 'x86_64-pc-linux-musl':
        domain = 'https://unofficial-builds.nodejs.org'
        suffix = 'linux-x64-musl.tar.gz'
    else:
        domain = 'https://nodejs.org'

        arch = ARCHITECTURES[platform.machine()]
        if windows:
            suffix = f'win-{arch}.zip'
        else:
            suffix = f'{platform.system().lower()}-{arch}.tar.gz'

    version = _node_version(domain, language_version)

    archive_name = f'node-{version}-{suffix}'
    with urlopen(
        urljoin(domain, f'download/release/{version}/{archive_name}'),
    ) as release:
        compressed = io.BytesIO(release.read())

    # TODO should i just extractall + rm the extra bits instead of partially
    #  extracting & renaming?

    if windows:
        # TODO this doesn't quite work
        def renamed_members(z: ZipFile) -> Generator[str, None, None]:
            prefix_len = len(f'{archive_name}/')
            for m in z.filelist:
                if WINDOWS_NODE_SUBDIRS.match(m.filename):
                    m.filename = m.filename[prefix_len:]
                    yield m.filename

        with ZipFile(compressed) as z:
            z.extractall(envdir, renamed_members(z))

        raise NotImplementedError('TODO')

    else:
        def rename_members_tf(tf: TarFile) -> Generator[TarInfo, None, None]:
            prefix_len = len(f'{archive_name}/')
            for m in tf.getmembers():
                if NIX_NODE_SUBDIRS.match(m.name):
                    m.path = m.path[prefix_len:]
                    yield m

        with TarFile.open(fileobj=compressed) as tf:
            tf.extractall(envdir, rename_members_tf(tf))  # type: ignore

        for file in ('npm', 'npx', 'node'):
            path = os.path.join(envdir, 'bin', file)
            os.chmod(path, os.stat(path).st_mode | 0o111)
        os.symlink('node', os.path.join(envdir, 'bin', 'nodejs'))

        return os.path.join(envdir, 'bin', 'npm')


def _node_version(domain: str, language_version: str) -> str:
    """Looks up the node.js version based on the configured
     version (uses the latest by default)"""
    if language_version == C.DEFAULT:
        # grab latest
        with urlopen(urljoin(domain, 'download/release/index.tab')) as index:
            _ = next(index)  # header
            version = next(index).split()[0].decode()
    else:
        version = f'v{language_version.replace("v", "")}'

    return version
