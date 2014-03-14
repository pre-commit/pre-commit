
import jsonschema
import jsonschema.exceptions
import os.path
import yaml

from pre_commit import git


def get_validator(
    default_filename,
    json_schema,
    exception_type,
    additional_validation_strategy=lambda obj: None,
):
    """Returns a function which will validate a yaml file for correctness

    Args:
        default_filename - Default filename to look for if none is specified
        json_schema - JSON schema to validate file with
        exception_type - Error type to raise on failure
        additional_validation_strategy - Strategy for additional validation of
            the object read from the file.  The function should either raise
            exception_type on failure.
    """

    def validate(filename=None):
        filename = filename or os.path.join(git.get_root(), default_filename)

        if not os.path.exists(filename):
            raise exception_type('File {0} does not exist'.format(filename))

        file_contents = open(filename, 'r').read()

        try:
            obj = yaml.load(file_contents)
        except Exception as e:
            raise exception_type(
                'File {0} is not a valid yaml file'.format(filename), e,
            )

        try:
            jsonschema.validate(obj, json_schema)
        except jsonschema.exceptions.ValidationError as e:
            raise exception_type(
                'File {0} is not a valid file'.format(filename), e,
            )

        additional_validation_strategy(obj)

        return obj

    return validate