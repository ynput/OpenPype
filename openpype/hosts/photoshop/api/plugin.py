import re

import avalon.api
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


class PhotoshopLoader(avalon.api.Loader):
    @staticmethod
    def get_stub():
        return stub()


class Creator(avalon.api.Creator):
    """Creator plugin to create instances in Photoshop

    A LayerSet is created to support any number of layers in an instance. If
    the selection is used, these layers will be added to the LayerSet.
    """

    def process(self):
        # Photoshop can have multiple LayerSets with the same name, which does
        # not work with Avalon.
        msg = "Instance with name \"{}\" already exists.".format(self.name)
        stub = lib.stub()  # only after Photoshop is up
        for layer in stub.get_layers():
            if self.name.lower() == layer.Name.lower():
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setText(msg)
                msg.exec_()
                return False

        # Store selection because adding a group will change selection.
        with lib.maintained_selection():

            # Add selection to group.
            if (self.options or {}).get("useSelection"):
                group = stub.group_selected_layers(self.name)
            else:
                group = stub.create_group(self.name)

            stub.imprint(group, self.data)

        return group
