import pytest

from pre_commit.languages.golang import guess_go_dir


@pytest.mark.parametrize(
    ('url', 'expected'),
    (
        ('/im/a/path/on/disk', 'unknown_src_dir'),
        ('file:///im/a/path/on/disk', 'unknown_src_dir'),
        ('git@github.com:golang/lint', 'github.com/golang/lint'),
        ('git://github.com/golang/lint', 'github.com/golang/lint'),
        ('http://github.com/golang/lint', 'github.com/golang/lint'),
        ('https://github.com/golang/lint', 'github.com/golang/lint'),
        ('ssh://git@github.com/golang/lint', 'github.com/golang/lint'),
        ('git@github.com:golang/lint.git', 'github.com/golang/lint'),
    ),
)
def test_guess_go_dir(url, expected):
    assert guess_go_dir(url) == expected
