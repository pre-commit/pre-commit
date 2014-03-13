#!/usr/bin/env python

if __name__ == '__main__':
    import sys

    from pre_commit.clientlib.validate_manifest import run

    sys.exit(run(sys.argv[1:]))