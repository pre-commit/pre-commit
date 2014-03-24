
import pre_commit.constants as C
from pre_commit.ordereddict import OrderedDict
from pre_commit.yaml_extensions import ordered_dump
from pre_commit.yaml_extensions import ordered_load


def test_ordered_load():
    ret = ordered_load(
        'a: herp\n'
        'c: derp\n'
        'd: darp\n'
        'b: harp\n'
    )
    # Original behavior
    assert ret == {'a': 'herp', 'b': 'harp', 'c': 'derp', 'd': 'darp'}
    # Ordered behavior
    assert (
        ret.items() ==
        [('a', 'herp'), ('c', 'derp'), ('d', 'darp'), ('b', 'harp')]
    )


def test_ordered_dump():
    ret = ordered_dump(
        OrderedDict(
            (('a', 'herp'), ('c', 'derp'), ('b', 'harp'), ('d', 'darp'))
        ),
        **C.YAML_DUMP_KWARGS
    )
    assert ret == (
        'a: herp\n'
        'c: derp\n'
        'b: harp\n'
        'd: darp\n'
    )
