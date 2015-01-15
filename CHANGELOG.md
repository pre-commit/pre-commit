0.3.5
=====
- Support running as `pre-push`.

0.3.4
=====
- Allow hook providers to default `args` in `hooks.yaml`

0.3.3
=====
- Improve message for `CalledProcessError`

0.3.2
=====
- Fix for `staged_files_only` with color.diff = always #176.

0.3.1
=====
- Fix error clobbering #174.
- Remove dependency on `plumbum`.
- Allow pre-commit to be run from anywhere in a repository #175.

0.3.0
=====
- Add `--files` option to `pre-commit run`

0.2.11
======
- Fix terminal width detection (broken in 0.2.10)

0.2.10
======
- Bump version of nodeenv to fix bug with ~/.npmrc
- Choose `python` more intelligently when running.

0.2.9
=====
- Fix bug where sys.stdout.write must take `bytes` in python 2.6

0.2.8
=====
- Allow a client to have duplicates of hooks.
- Use --prebuilt instead of system for node.
- Improve some fatal error messages

0.2.7
=====
- Produce output when running pre-commit install --install-hooks

0.2.6
=====
- Print hookid on failure
- Use sys.executable for running nodeenv
- Allow running as `python -m pre_commit`

0.2.5
=====
- Default columns to 80 (for non-terminal execution).

0.2.4
=====
- Support --install-hooks as an argument to `pre-commit install`
- Install hooks before attempting to run anything
- Use `python -m nodeenv` instead of `nodeenv`

0.2.3
=====
- Freeze ruby building infrastructure
- Fix bug that assumed diffs were utf-8

0.2.2
=====
- Fix filenames with spaces

0.2.1
=====
- Use either `pre-commit` or `python -m pre_commit.main` depending on which is
  available
- Don't use readlink -f

0.2.0
=====
- Fix for merge-conflict during cherry-picking.
- Add -V / --version
- Add migration install mode / install -f / --overwrite
- Add `pcre` "language" for perl compatible regexes
- Reorganize packages.

0.1.1
=====
- Fixed bug with autoupdate setting defaults on un-updated repos.


0.1
===
- Initial Release
