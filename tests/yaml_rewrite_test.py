from __future__ import annotations

import pytest

from pre_commit.yaml import yaml_compose
from pre_commit.yaml_rewrite import MappingKey
from pre_commit.yaml_rewrite import MappingValue
from pre_commit.yaml_rewrite import match
from pre_commit.yaml_rewrite import SequenceItem


def test_match_produces_scalar_values_only():
    src = '''\
-   name: foo
-   name: [not, foo]  # not a scalar: should be skipped!
-   name: bar
'''
    matcher = (SequenceItem(), MappingValue('name'))
    ret = [n.value for n in match(yaml_compose(src), matcher)]
    assert ret == ['foo', 'bar']


@pytest.mark.parametrize('cls', (MappingKey, MappingValue))
def test_mapping_not_a_map(cls):
    m = cls('s')
    assert list(m.match(yaml_compose('[foo]'))) == []


def test_sequence_item_not_a_sequence():
    assert list(SequenceItem().match(yaml_compose('s: val'))) == []


def test_mapping_key():
    m = MappingKey('s')
    ret = [n.value for n in m.match(yaml_compose('s: val\nt: val2'))]
    assert ret == ['s']


def test_mapping_value():
    m = MappingValue('s')
    ret = [n.value for n in m.match(yaml_compose('s: val\nt: val2'))]
    assert ret == ['val']


def test_sequence_item():
    ret = [n.value for n in SequenceItem().match(yaml_compose('[a, b, c]'))]
    assert ret == ['a', 'b', 'c']
