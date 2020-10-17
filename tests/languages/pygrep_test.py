import pytest

from pre_commit.languages import pygrep


@pytest.fixture
def some_files(tmpdir):
    tmpdir.join('f1').write_binary(b'foo\nbar\n')
    tmpdir.join('f2').write_binary(b'[INFO] hi\n')
    tmpdir.join('f3').write_binary(b"with'quotes\n")
    tmpdir.join('f4').write_binary(b'foo\npattern\nbar\n')
    tmpdir.join('f5').write_binary(b'[INFO] hi\npattern\nbar')
    tmpdir.join('f6').write_binary(b"pattern\nbarwith'foo\n")
    with tmpdir.as_cwd():
        yield


@pytest.mark.usefixtures('some_files')
@pytest.mark.parametrize(
    ('pattern', 'expected_retcode', 'expected_out'),
    (
        ('baz', 0, ''),
        ('foo', 1, 'f1:1:foo\n'),
        ('bar', 1, 'f1:2:bar\n'),
        (r'(?i)\[info\]', 1, 'f2:1:[INFO] hi\n'),
        ("h'q", 1, "f3:1:with'quotes\n"),
    ),
)
def test_main(cap_out, pattern, expected_retcode, expected_out):
    ret = pygrep.main((pattern, 'f1', 'f2', 'f3'))
    out = cap_out.get()
    assert ret == expected_retcode
    assert out == expected_out


@pytest.mark.usefixtures('some_files')
def test_negate_by_line_no_match(cap_out):
    ret = pygrep.main(('pattern\nbar', 'f4', 'f5', 'f6', '--negate'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f4\nf5\nf6\n'


@pytest.mark.usefixtures('some_files')
def test_negate_by_line_two_match(cap_out):
    ret = pygrep.main(('foo', 'f4', 'f5', 'f6', '--negate'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f5\n'


@pytest.mark.usefixtures('some_files')
def test_negate_by_line_all_match(cap_out):
    ret = pygrep.main(('pattern', 'f4', 'f5', 'f6', '--negate'))
    out = cap_out.get()
    assert ret == 0
    assert out == ''


@pytest.mark.usefixtures('some_files')
def test_negate_by_file_no_match(cap_out):
    ret = pygrep.main(('baz', 'f4', 'f5', 'f6', '--negate', '--multiline'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f4\nf5\nf6\n'


@pytest.mark.usefixtures('some_files')
def test_negate_by_file_one_match(cap_out):
    ret = pygrep.main(
        ('foo\npattern', 'f4', 'f5', 'f6', '--negate', '--multiline'),
    )
    out = cap_out.get()
    assert ret == 1
    assert out == 'f5\nf6\n'


@pytest.mark.usefixtures('some_files')
def test_negate_by_file_all_match(cap_out):
    ret = pygrep.main(
        ('pattern\nbar', 'f4', 'f5', 'f6', '--negate', '--multiline'),
    )
    out = cap_out.get()
    assert ret == 0
    assert out == ''


@pytest.mark.usefixtures('some_files')
def test_ignore_case(cap_out):
    ret = pygrep.main(('--ignore-case', 'info', 'f1', 'f2', 'f3'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f2:1:[INFO] hi\n'


@pytest.mark.usefixtures('some_files')
def test_multiline(cap_out):
    ret = pygrep.main(('--multiline', r'foo\nbar', 'f1', 'f2', 'f3'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f1:1:foo\nbar\n'


@pytest.mark.usefixtures('some_files')
def test_multiline_line_number(cap_out):
    ret = pygrep.main(('--multiline', r'ar', 'f1', 'f2', 'f3'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f1:2:bar\n'


@pytest.mark.usefixtures('some_files')
def test_multiline_dotall_flag_is_enabled(cap_out):
    ret = pygrep.main(('--multiline', r'o.*bar', 'f1', 'f2', 'f3'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f1:1:foo\nbar\n'


@pytest.mark.usefixtures('some_files')
def test_multiline_multiline_flag_is_enabled(cap_out):
    ret = pygrep.main(('--multiline', r'foo$.*bar', 'f1', 'f2', 'f3'))
    out = cap_out.get()
    assert ret == 1
    assert out == 'f1:1:foo\nbar\n'
