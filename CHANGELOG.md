0.5.4
=====
- Allow hooks to produce outputs with arbitrary bytes
- Fix pre-commit install when .git/hooks/pre-commit is a dead symlink
- Allow an unstaged config when using --files or --all-files

0.5.3
=====
- Fix autoupdate with "local" hooks - don't purge local hooks.

0.5.2
=====
- Fix autoupdate with "local" hooks

0.5.1
=====
- Fix bug with unknown non-ascii hook-id
- Avoid crash when .git/hooks is not present in some git clients

0.5.0
=====
- Add a new "local" hook type for running hooks without remote configuration.
- Complain loudly when .pre-commit-config.yaml is unstaged.
- Better support for multiple language versions when running hooks.
- Allow exclude to be defaulted in repository configuration.

0.4.4
=====
- Use sys.executable when executing virtualenv

0.4.3
=====
- Use reset instead of checkout when checkout out hook repo

0.4.2
=====
- Limit length of xargs arguments to workaround windows xargs bug

0.4.1
=====
- Don't rename across devices when creating sqlite database

0.4.0
=====
- Make ^C^C During installation not cause all subsequent runs to fail
- Print while installing (instead of while cloning)
- Use sqlite to manage repositories (instead of symlinks)
- MVP Windows support

0.3.6
=====
- `args` in venv'd languages are now property quoted.

0.3.5
=====
- Support running during `pre-push`.  See http://pre-commit.com/#advanced 'pre-commit during push'.

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
