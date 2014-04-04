
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.jsonschema_extensions import remove_defaults


def test_apply_defaults_copies_object():
    input = {}
    ret = apply_defaults(input, {})
    assert ret is not input


def test_apply_default_does_not_touch_schema_without_defaults():
    ret = apply_defaults(
        {'foo': 'bar'},
        {'type': 'object', 'properties': {'foo': {}, 'baz': {}}},
    )
    assert ret == {'foo': 'bar'}


def test_apply_defaults_applies_defaults():
    ret = apply_defaults(
        {'foo': 'bar'},
        {
            'type': 'object',
            'properties': {
                'foo': {'default': 'biz'},
                'baz': {'default': 'herp'},
            }
        }
    )
    assert ret == {'foo': 'bar', 'baz': 'herp'}


def test_apply_defaults_deep():
    ret = apply_defaults(
        {'foo': {'bar': {}}},
        {
            'type': 'object',
            'properties': {
                'foo': {
                    'type': 'object',
                    'properties': {
                        'bar': {
                            'type': 'object',
                            'properties': {'baz': {'default': 'herp'}},
                        },
                    },
                },
            },
        },
    )
    assert ret == {'foo': {'bar': {'baz': 'herp'}}}


def test_apply_defaults_copies():
    schema = {'properties': {'foo': {'default': []}}}
    ret1 = apply_defaults({}, schema)
    ret2 = apply_defaults({}, schema)
    assert ret1['foo'] is not ret2['foo']


def test_remove_defaults_copies_object():
    input = {}
    ret = remove_defaults(input, {})
    assert ret is not input


def test_remove_defaults_does_not_remove_non_default():
    ret = remove_defaults(
        {'foo': 'bar'},
        {'properties': {'foo': {'default': 'baz'}}},
    )
    assert ret == {'foo': 'bar'}


def test_remove_defaults_removes_default():
    ret = remove_defaults(
        {'foo': 'bar'},
        {'properties': {'foo': {'default': 'bar'}}},
    )
    assert ret == {}
