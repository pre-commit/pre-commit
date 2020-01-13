import io

from pre_commit import output


def test_output_write_writes():
    stream = io.BytesIO()
    output.write('hello world', stream)
    assert stream.getvalue() == b'hello world'
