import yaml

from pre_commit.ordereddict import OrderedDict


# Adapted from http://stackoverflow.com/a/21912744/812183

def ordered_load(stream):
    class OrderedLoader(yaml.loader.Loader):
        pass

    def constructor(loader, node):
        return OrderedDict(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        constructor,
    )
    return yaml.load(stream, Loader=OrderedLoader)


def ordered_dump(obj, **kwargs):
    class OrderedDumper(yaml.dumper.SafeDumper):
        pass

    def dict_representer(dumper, data):
        return dumper.represent_mapping(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            data.items(),
        )
    OrderedDumper.add_representer(OrderedDict, dict_representer)
    return yaml.dump(obj, Dumper=OrderedDumper, **kwargs)
