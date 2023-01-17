from __future__ import annotations

from pre_commit.languages import perl
from pre_commit.store import _make_local_repo
from pre_commit.util import make_executable
from testing.language_helpers import run_language


def test_perl_install(tmp_path):
    makefile_pl = '''\
use strict;
use warnings;

use ExtUtils::MakeMaker;

WriteMakefile(
    NAME => "PreCommitHello",
    VERSION_FROM => "lib/PreCommitHello.pm",
    EXE_FILES => [qw(bin/pre-commit-perl-hello)],
);
'''
    bin_perl_hello = '''\
#!/usr/bin/env perl

use strict;
use warnings;
use PreCommitHello;

PreCommitHello::hello();
'''
    lib_hello_pm = '''\
package PreCommitHello;

use strict;
use warnings;

our $VERSION = "0.1.0";

sub hello {
    print "Hello from perl-commit Perl!\n";
}

1;
'''
    tmp_path.joinpath('Makefile.PL').write_text(makefile_pl)
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    exe = bin_dir.joinpath('pre-commit-perl-hello')
    exe.write_text(bin_perl_hello)
    make_executable(exe)
    lib_dir = tmp_path.joinpath('lib')
    lib_dir.mkdir()
    lib_dir.joinpath('PreCommitHello.pm').write_text(lib_hello_pm)

    ret = run_language(tmp_path, perl, 'pre-commit-perl-hello')
    assert ret == (0, b'Hello from perl-commit Perl!\n')


def test_perl_additional_dependencies(tmp_path):
    _make_local_repo(str(tmp_path))

    ret, out = run_language(
        tmp_path,
        perl,
        'perltidy --version',
        deps=('SHANCOCK/Perl-Tidy-20211029.tar.gz',),
    )
    assert ret == 0
    assert out.startswith(b'This is perltidy, v20211029')
