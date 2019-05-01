import argparse

from pre_commit import output


def sign_commit():
    pass


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('retval', nargs='*', default=0)
    args = parser.parse_args(argv)
    output.write_line(f'Signing commit message if {args.retval}')
    if args.retval:
        return 1
    return 0


if __name__ == '__main__':
    exit(main())
