# -*- coding: utf-8 -*-
"""Creator plugin for creating publishable Houdini Digital Assets."""
from openpype.client import (
    get_asset_by_name,
    get_subsets,
)
from openpype.pipeline import legacy_io
from openpype.hosts.houdini.api import (lib, plugin)


class CreateHDA(plugin.HoudiniCreator):
    """Publish Houdini Digital Asset file."""

    identifier = "hda"
    label = "Houdini Digital Asset (Hda)"
    family = "hda"
    icon = "gears"
    maintain_selection = False

    def _check_existing(self, subset_name):
        # type: (str) -> bool
        """Check if existing subset name versions already exists."""
        # Get all subsets of the current asset
        project_name = legacy_io.active_project()
        asset_doc = get_asset_by_name(
            project_name, self.data["asset"], fields=["_id"]
        )
        subset_docs = get_subsets(
            project_name, asset_ids=[asset_doc["_id"]], fields=["name"]
        )
        existing_subset_names_low = {
            subset_doc["name"].lower()
            for subset_doc in subset_docs
        }
        return subset_name.lower() in existing_subset_names_low

    def create(self, subset_name, instance_data, pre_create_data):
        import hou

        instance_data.pop("active", None)

        instance = super(CreateHDA, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))
        out = hou.node("/obj")
        if self._nodes:
            # if we have `use selection` enabled, and we have some
            # selected nodes ...
            subnet = out.collapseIntoSubnet(
                self.nodes,
                subnet_name="{}_subnet".format(subset_name))
            subnet.moveToGoodPosition()
            to_hda = subnet
        else:
            to_hda = out.createNode(
                "subnet", node_name="{}_subnet".format(subset_name))
        if not to_hda.type().definition():
            # if node type has not its definition, it is not user
            # created hda. We test if hda can be created from the node.
            if not to_hda.canCreateDigitalAsset():
                raise plugin.OpenPypeCreatorError(
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

        return hda_node
