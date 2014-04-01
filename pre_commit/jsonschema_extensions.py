
import copy
import jsonschema
import jsonschema.validators


# From https://github.com/Julian/jsonschema/blob/master/docs/faq.rst
def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

        for property, subschema in properties.iteritems():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

    return jsonschema.validators.extend(
        validator_class, {"properties" : set_defaults},
    )


DefaultingValidator = extend_with_default(jsonschema.Draft4Validator)


def apply_defaults(obj, schema):
    obj = copy.deepcopy(obj)
    DefaultingValidator(schema).validate(obj)
    return obj
