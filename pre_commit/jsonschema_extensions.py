from __future__ import unicode_literals

import copy

import jsonschema
import jsonschema.validators


# From https://github.com/Julian/jsonschema/blob/master/docs/faq.rst
def extend_validator_cls(validator_cls, modify):
    validate_properties = validator_cls.VALIDATORS['properties']

    def new_properties(validator, properties, instance, schema):
        # Exhaust the validator
        list(validate_properties(validator, properties, instance, schema))
        modify(properties, instance)

    return jsonschema.validators.extend(
        validator_cls, {'properties': new_properties},
    )


def default_values(properties, instance):
    for prop, subschema in properties.items():
        if 'default' in subschema:
            instance.setdefault(
                prop, copy.deepcopy(subschema['default']),
            )


def remove_default_values(properties, instance):
    for prop, subschema in properties.items():
        if (
                'default' in subschema and
                instance.get(prop) == subschema['default']
        ):
            del instance[prop]


_AddDefaultsValidator = extend_validator_cls(
    jsonschema.Draft4Validator, default_values,
)
_RemoveDefaultsValidator = extend_validator_cls(
    jsonschema.Draft4Validator, remove_default_values,
)


def apply_defaults(obj, schema):
    obj = copy.deepcopy(obj)
    _AddDefaultsValidator(schema).validate(obj)
    return obj


def remove_defaults(obj, schema):
    obj = copy.deepcopy(obj)
    _RemoveDefaultsValidator(schema).validate(obj)
    return obj
