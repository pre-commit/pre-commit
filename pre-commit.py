#!/usr/bin/env python

import collections
import optparse
import os
import os.path
import shutil
import subprocess
import sys

def __backport_check_output():
    def check_output(*popenargs, **kwargs):
        r"""Run command with arguments and return its output as a byte string.

        Backported from Python 2.7 as it's implemented as pure python on stdlib.

        >>> check_output(['/usr/bin/python', '--version'])
        Python 2.6.2
        """
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            error = subprocess.CalledProcessError(retcode, cmd)
            error.output = output
            raise error
        return output

    if not hasattr(subprocess, 'check_output'):
        setattr(subprocess, 'check_output', check_output)

__backport_check_output()
del __backport_check_output


FILE_LIST = 'git ls-files | egrep "\.%s$"'

ALL_FILES = FILE_LIST % '(php|sql|py|js|htm|c|cpp|h|sh|css)'
JS_FILES = FILE_LIST % 'js'
PY_FILES = FILE_LIST % 'py'
CPP_FILES = FILE_LIST % '(cc|cpp|h)'
C_FILES = FILE_LIST % '(c|h)'
C_LIKE_FILES = FILE_LIST % '(c|cc|cpp|h)'
HEADER_FILES = FILE_LIST % 'h'

RED = '\033[41m'
GREEN = '\033[42m'
NORMAL = '\033[0m'
COLS = int(subprocess.check_output(['tput', 'cols']))

Test = collections.namedtuple('Test', ['command', 'name', 'nonzero', 'config'])

TESTS = [
    Test(
        "%s | xargs pyflakes" % PY_FILES,
        'Py    - Pyflakes',
        False, 'testpyflakes',
    ),
    Test(
        "%s | xargs grep 'import\sipdb'" % PY_FILES,
        'Py    - ipdb',
        True, 'testipdb',
    ),
    Test(
        "%s | grep 'tests' | grep -v '_test.py$' | grep -v '__init__.py' | grep -v '/conftest.py'" % PY_FILES,
        'Py    - Test files should end in _test.py',
        True, 'testtestnames',
    ),
    Test(
        "%s | xargs egrep 'split\(.\\\\n.\)'" % PY_FILES,
        'Py    - Use s.splitlines over s.split',
        True, 'testsplitlines',
    ),
    Test(
        "%s | xargs grep -H -n -P '\t'" % ALL_FILES,
        "All   - No tabs",
        True, 'testtabs',
    ),
]

def get_git_config(config_name):
    config_result = ''
    try:
        config_result = subprocess.check_output([
            'git', 'config', config_name
        ])
    except subprocess.CalledProcessError: pass

    return config_result.strip()

def get_pre_commit_path():
    git_top = subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel']
    ).strip()
    return os.path.join(git_top, '.git/hooks/pre-commit')

class FixAllBase(object):
    name = None
    matching_files_command = None

    def get_all_files(self):
        try:
            files = subprocess.check_output(
                self.matching_files_command,
                shell=True,
            )
            files_split = files.splitlines()
            return [file.strip() for file in files_split]
        except subprocess.CalledProcessError:
            return []

    def fix_file(self, file):
        '''Implement to fix the file.'''
        raise NotImplementedError

    def run(self):
        '''Runs the process to fix the files. Returns True if nothign to fix.'''
        print '%s...' % self.name
        all_files = self.get_all_files()
        for file in all_files:
            print 'Fixing %s' % file
            self.fix_file(file)
        return not all_files

class FixTrailingWhitespace(FixAllBase):
    name = 'Trimming trailing whitespace'
    matching_files_command = '%s | xargs egrep -l "[[:space:]]$"' % ALL_FILES

    def fix_file(self, file):
        subprocess.check_call(['sed', '-i', '-e', 's/[[:space:]]*$//', file])

class FixLineEndings(FixAllBase):
    name = 'Fixing line endings'
    matching_files_command = "%s | xargs egrep -l $'\\r'\\$" % ALL_FILES

    def fix_file(self, file):
        subprocess.check_call(['dos2unix', file])
        subprocess.check_call(['mac2unix', file])

FIXERS = [
    FixTrailingWhitespace,
    FixLineEndings,
]

def run_tests():
    passed = True
    for test in TESTS:
        run_test = get_git_config('hooks.%s' % test.config)
        if run_test == 'false':
            print 'Skipping "%s" due to git config.' % test.name
            continue

        try:
            retcode = 0
            output = subprocess.check_output(
                test.command, shell=True, stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            retcode = e.returncode
            output = e.output

        pass_fail = '%sSuccess%s' % (GREEN, NORMAL)
        failed_test = False
        if (retcode and not test.nonzero) or (not retcode and test.nonzero):
            pass_fail = '%sFailure(%s)%s' % (RED, retcode, NORMAL)
            failed_test = True

        dots = COLS - len(pass_fail) - len(test.name)
        print '%s%s%s' % (test.name, '.' * dots, pass_fail)

        if failed_test:
            print
            print output
            passed = False

    return passed

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option(
        '-u', '--uninstall',
        action='store_true', dest='uninstall', default=False,
        help='Uninstall pre-commit script.'
    )
    parser.add_option(
        '-i', '--install',
        action='store_true', dest='install', default=False,
        help='Install pre-commit script.'
    )
    opts, args = parser.parse_args()

    if opts.install:
        pre_commit_path = get_pre_commit_path()
        shutil.copyfile(__file__, pre_commit_path)
        os.chmod(pre_commit_path, 0755)
        print 'Installed pre commit to %s' % pre_commit_path
        sys.exit(0)
    elif opts.uninstall:
        pre_commit_path = get_pre_commit_path()
        if os.path.exists(pre_commit_path):
            os.remove(pre_commit_path)
        print 'Removed pre-commit scripts.'

    passed = True
    for fixer in FIXERS:
        passed &= fixer().run()
    passed &= run_tests()

    if not passed:
        print '%sFailures / Fixes detected.%s' % (RED, NORMAL)
        print 'Please fix and commit again.'
        print "You could also pass --no-verify, but you probably shouldn't."
        print
        print "Here's git status for convenience: "
        print
        os.system('git status')
        sys.exit(-1)
