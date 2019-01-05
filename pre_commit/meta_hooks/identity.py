import sys

from pre_commit import output


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    for arg in argv:
        output.write_line(arg)


if __name__ == '__main__':
    exit(main())
