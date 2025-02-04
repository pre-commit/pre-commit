from __future__ import annotations

import os
import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.languages import pipenv
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from testing.language_helpers import run_language

def test_health_check_no_pipfile(tmp_path):
    with pytest.raises(AssertionError) as excinfo:
        pipenv.health_check(Prefix(str(tmp_path)), C.DEFAULT)
    assert '`language: pipenv` requires a Pipfile' in str(excinfo.value)

def _make_pipfile(path):
    with open(os.path.join(path, 'Pipfile'), 'w') as f:
        f.write('''\
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"

[dev-packages]
pytest = "*"

[requires]
python_version = "3.9"
''')

def test_health_check_with_pipfile(tmp_path):
    _make_pipfile(tmp_path)
    assert pipenv.health_check(Prefix(str(tmp_path)), C.DEFAULT) is None

def test_install_environment(tmp_path):
    _make_pipfile(tmp_path)
    
    with mock.patch.object(pipenv, 'cmd_output_b') as mocked:
        pipenv.install_environment(
            Prefix(str(tmp_path)), 
            C.DEFAULT, 
            ['black']
        )
        
        python_version = f"{sys.version_info[0]}.{sys.version_info[1]}"
        assert mocked.call_args_list == [
            mock.call('pipenv', '--python', python_version),
            mock.call('pipenv', 'install', '--dev'),
            mock.call('pipenv', 'install', 'black'),
        ]

def test_run_hook(tmp_path):
    _make_pipfile(tmp_path)
    
    # Create a simple Python script
    script = '''\
#!/usr/bin/env python
print("Hello from pipenv!")
'''
    tmp_path.joinpath('script.py').write_text(script)
    
    ret = run_language(
        tmp_path,
        pipenv,
        'python script.py',
    )
    assert ret == (0, b'Hello from pipenv!\n') 