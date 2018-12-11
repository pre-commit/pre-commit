from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
import textwrap

from pre_commit.languages import python


def test_norm_version_expanduser():
    home = os.path.expanduser('~')
    if os.name == 'nt':  # pragma: no cover (nt)
        path = r'~\python343'
        expected_path = r'{}\python343'.format(home)
    else:  # pragma: no cover (non-nt)
        path = '~/.pyenv/versions/3.4.3/bin/python'
        expected_path = home + '/.pyenv/versions/3.4.3/bin/python'
    result = python.norm_version(path)
    assert result == expected_path


def test_single_requirements_file(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pep8
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'req1.txt'],
    ) == ['pep8']
    assert python.collect_requirements(
        tmpdir, ['-rreq1.txt'],
    ) == ['pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req1.txt'],
    ) == ['pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement=req1.txt'],
    ) == ['pep8']


def test_multiple_requirements_file(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pep8
        '''))
    req2 = os.path.join(tmpdir, 'req2.txt')
    with open(req2, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pre-commit
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'req1.txt', '-r', 'req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['-rreq1.txt', '-rreq2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req1.txt', '--requirement', 'req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement=req1.txt', '--requirement=req2.txt'],
    ) == ['pep8', 'pre-commit']


def test_nested_requirements_file(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pep8
        '''))
    req2 = os.path.join(tmpdir, 'req2.txt')
    with open(req2, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            -r req1.txt
            pre-commit
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['-rreq2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement=req2.txt'],
    ) == ['pep8', 'pre-commit']


def test_nested_requirements_files_subdir(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pep8
        '''))
    reqsdir = os.path.join(tmpdir, 'requirements')
    os.makedirs(reqsdir)
    req2 = os.path.join(reqsdir, 'req2.txt')
    with open(req2, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            -r ../req1.txt
            pre-commit
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'requirements/req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['-rrequirements/req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'requirements/req2.txt'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement=requirements/req2.txt'],
    ) == ['pep8', 'pre-commit']


def test_mixed_requirements(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pep8
        '''))
    assert python.collect_requirements(
        tmpdir, ['pre-commit', '-r', 'req1.txt'],
    ) == ['pre-commit', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['-rreq1.txt', 'pre-commit'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req1.txt', 'pre-commit'],
    ) == ['pep8', 'pre-commit']
    assert python.collect_requirements(
        tmpdir, ['pre-commit', '--requirement=req1.txt'],
    ) == ['pre-commit', 'pep8']


def test_options_in_requirements_file(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            --index-url=https://domain.tld/repository/pypi/simple/
            pep8
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'req1.txt'],
    ) == ['--index-url=https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['-rreq1.txt'],
    ) == ['--index-url=https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req1.txt'],
    ) == ['--index-url=https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement=req1.txt'],
    ) == ['--index-url=https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir,
        [
            '--index-url=https://domain.tld/repository/pypi/simple/',
            '-r', 'req1.txt',
        ],
    ) == ['--index-url=https://domain.tld/repository/pypi/simple/', 'pep8']
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            --index-url https://domain.tld/repository/pypi/simple/
            pep8
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'req1.txt'],
    ) == ['--index-url', 'https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['-rreq1.txt'],
    ) == ['--index-url', 'https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req1.txt'],
    ) == ['--index-url', 'https://domain.tld/repository/pypi/simple/', 'pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement=req1.txt'],
    ) == ['--index-url', 'https://domain.tld/repository/pypi/simple/', 'pep8']


def test_missing_requirements_file(tempdir_factory):
    tmpdir = tempdir_factory.get()
    req1 = os.path.join(tmpdir, 'req1.txt')
    with open(req1, 'w') as wfh:
        wfh.write(textwrap.dedent('''
            # This is a comment in the pip file
            pep8
        '''))
    assert python.collect_requirements(
        tmpdir, ['-r', 'req1.txt', '-r', 'req2.txt'],
    ) == ['pep8']
    assert python.collect_requirements(
        tmpdir, ['-rreq1.txt', '-rreq2.txt'],
    ) == ['pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement', 'req1.txt', '--requirement', 'req2.txt'],
    ) == ['pep8']
    assert python.collect_requirements(
        tmpdir, ['--requirement=req1.txt', '--requirement=req2.txt'],
    ) == ['pep8']
