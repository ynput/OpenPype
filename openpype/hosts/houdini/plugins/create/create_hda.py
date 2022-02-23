# -*- coding: utf-8 -*-
import hou
from avalon import io
from openpype.hosts.houdini.api import lib
from openpype.hosts.houdini.api import plugin


class CreateHDA(plugin.Creator):
    """Publish Houdini Digital Asset file."""

    name = "hda"
    label = "Houdini Digital Asset (Hda)"
    family = "hda"
    icon = "gears"
    maintain_selection = False

    def __init__(self, *args, **kwargs):
        super(CreateHDA, self).__init__(*args, **kwargs)
        self.data.pop("active", None)

    def _check_existing(self, subset_name):
        # type: (str) -> bool
        """Check if existing subset name versions already exists."""
        # Get all subsets of the current asset
        asset_id = io.find_one({"name": self.data["asset"], "type": "asset"},
                               projection={"_id": True})['_id']
        subset_docs = io.find(
            {
                "type": "subset",
                "parent": asset_id
            }, {"name": 1}
        )
        existing_subset_names = set(subset_docs.distinct("name"))
        existing_subset_names_low = {
            _name.lower() for _name in existing_subset_names
        }
        return subset_name.lower() in existing_subset_names_low

    def _process(self, instance):
        subset_name = self.data["subset"]
        # get selected nodes
        out = hou.node("/obj")
        self.nodes = hou.selectedNodes()

        if (self.options or {}).get("useSelection") and self.nodes:
            # if we have `use selection` enabled and we have some
            # selected nodes ...
            subnet = out.collapseIntoSubnet(
                self.nodes,
                subnet_name="{}_subnet".format(self.name))
            subnet.moveToGoodPosition()
            to_hda = subnet
        else:
            to_hda = out.createNode(
                "subnet", node_name="{}_subnet".format(self.name))
        if not to_hda.type().definition():
            # if node type has not its definition, it is not user
            # created hda. We test if hda can be created from the node.
            if not to_hda.canCreateDigitalAsset():
                raise Exception(
                    "cannot create hda from node {}".format(to_hda))

            hda_node = to_hda.createDigitalAsset(
                name=subset_name,
                hda_file_name="$HIP/{}.hda".format(subset_name)
            )
            hda_node.layoutChildren()
        elif self._check_existing(subset_name):
            raise plugin.OpenPypeCreatorError(
                ("subset {} is already published with different HDA"
                 "definition.").format(subset_name))
        else:
            hda_node = to_hda

        hda_node.setName(subset_name)

        # delete node created by Avalon in /out
        # this needs to be addressed in future Houdini workflow refactor.

        hou.node("/out/{}".format(subset_name)).destroy()

        try:
            lib.imprint(hda_node, self.data)
        except hou.OperationFailed:
            raise plugin.OpenPypeCreatorError(
                ("Cannot set metadata on asset. Might be that it already is "
                 "OpenPype asset.")
            )

        return hda_node
