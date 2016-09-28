from ruamel import yaml


def yaml_dump(obj, **kwargs):
    "Ensure order & comments preservation"
    return yaml.dump(obj, Dumper=yaml.RoundTripDumper, **kwargs)


def yaml_load(content):
    "Ensure order & comments preservation"
    return yaml.load(content, Loader=yaml.RoundTripLoader)
