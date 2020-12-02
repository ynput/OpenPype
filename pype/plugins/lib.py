import re
import json
import os


def get_unique_layer_name(layers, name):
    """
        Gets all layer names and if 'name' is present in them, increases
        suffix by 1 (eg. creates unique layer name - for Loader)
    Args:
        layers (list): of strings, names only
        name (string):  checked value

    Returns:
        (string): name_00X (without version)
    """
    names = {}
    for layer in layers:
        layer_name = re.sub(r'_\d{3}$', '', layer)
        if layer_name in names.keys():
            names[layer_name] = names[layer_name] + 1
        else:
            names[layer_name] = 1
    occurrences = names.get(name, 0)

    return "{}_{:0>3d}".format(name, occurrences + 1)


def get_background_layers(file_url):
    """
        Pulls file name from background json file, enrich with folder url for
        AE to be able import files.

        Order is important, follows order in json.

        Args:
            file_url (str): abs url of background json

        Returns:
            (list): of abs paths to images
    """
    with open(file_url) as json_file:
        data = json.load(json_file)

    layers = list()
    bg_folder = os.path.dirname(file_url)
    for child in data['children']:
        if child.get("filename"):
            layers.append(os.path.join(bg_folder, child.get("filename")).
                          replace("\\", "/"))
        else:
            for layer in child['children']:
                if layer.get("filename"):
                    layers.append(os.path.join(bg_folder,
                                               layer.get("filename")).
                                  replace("\\", "/"))
    return layers
