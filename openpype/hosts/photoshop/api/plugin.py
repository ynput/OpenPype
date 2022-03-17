import re

from openpype.pipeline import LoaderPlugin
from .launch_logic import stub


def get_unique_layer_name(layers, asset_name, subset_name):
    """
        Gets all layer names and if 'asset_name_subset_name' is present, it
        increases suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list) of dict with layers info (name, id etc.)
        asset_name (string):
        subset_name (string):

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


class PhotoshopLoader(LoaderPlugin):
    @staticmethod
    def get_stub():
        return stub()
