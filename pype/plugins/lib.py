import re


def get_unique_layer_name(layers, asset_name, subset_name):
    """
        Gets all layer names and if 'name' is present in them, increases
        suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list): of namedtuples, expects 'name' field present
        asset_name (string):  in format asset_subset (Hero)
        subset_name (string): (LOD)

    Returns:
        (string): name_00X (without version)
    """
    name = "{}_{}".format(asset_name, subset_name)
    names = {}
    for layer in layers:
        layer_name = re.sub(r'_\d{3}$', '', layer.name)
        if layer_name in names.keys():
            names[layer_name] = names[layer_name] + 1
        else:
            names[layer_name] = 1
    occurrences = names.get(name, 0)

    return "{}_{:0>3d}".format(name, occurrences + 1)
