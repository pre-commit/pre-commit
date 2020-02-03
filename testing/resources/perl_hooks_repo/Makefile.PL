use strict;
use warnings;

use ExtUtils::MakeMaker;

WriteMakefile(
    NAME => "PreCommitHello",
    VERSION_FROM => "lib/PreCommitHello.pm",
    EXE_FILES => [qw(bin/pre-commit-perl-hello)],
);
