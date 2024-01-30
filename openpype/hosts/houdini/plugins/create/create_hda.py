# -*- coding: utf-8 -*-
"""Creator plugin for creating publishable Houdini Digital Assets."""
from openpype.client import (
    get_asset_by_name,
    get_subsets,
)
from openpype.hosts.houdini.api import plugin
import hou


class CreateHDA(plugin.HoudiniCreator):
    """Publish Houdini Digital Asset file."""

    identifier = "io.openpype.creators.houdini.hda"
    label = "Houdini Digital Asset (Hda)"
    family = "hda"
    icon = "gears"
    maintain_selection = False

    def _check_existing(self, asset_name, subset_name):
        # type: (str) -> bool
        """Check if existing subset name versions already exists."""
        # Get all subsets of the current asset
        project_name = self.project_name
        asset_doc = get_asset_by_name(
            project_name, asset_name, fields=["_id"]
        )
        subset_docs = get_subsets(
            project_name, asset_ids=[asset_doc["_id"]], fields=["name"]
        )
        existing_subset_names_low = {
            subset_doc["name"].lower()
            for subset_doc in subset_docs
        }
        return subset_name.lower() in existing_subset_names_low

    def create_instance_node(
        self, asset_name, node_name, parent, node_type="geometry"
    ):

        parent_node = hou.node("/obj")
        if self.selected_nodes:
            # if we have `use selection` enabled, and we have some
            # selected nodes ...
            subnet = parent_node.collapseIntoSubnet(
                self.selected_nodes,
                subnet_name="{}_subnet".format(node_name))
            subnet.moveToGoodPosition()
            to_hda = subnet
        else:
            to_hda = parent_node.createNode(
                "subnet", node_name="{}_subnet".format(node_name))
        if not to_hda.type().definition():
            # if node type has not its definition, it is not user
            # created hda. We test if hda can be created from the node.
            if not to_hda.canCreateDigitalAsset():
                raise plugin.OpenPypeCreatorError(
                    "cannot create hda from node {}".format(to_hda))

            hda_node = to_hda.createDigitalAsset(
                name=node_name,
                hda_file_name="$HIP/{}.hda".format(node_name)
            )
            hda_node.layoutChildren()
        elif self._check_existing(asset_name, node_name):
            raise plugin.OpenPypeCreatorError(
                ("subset {} is already published with different HDA"
                 "definition.").format(node_name))
        else:
            hda_node = to_hda

        hda_node.setName(node_name)
        self.customize_node_look(hda_node)
        return hda_node

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data.pop("active", None)

        instance = super(CreateHDA, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: plugin.CreatedInstance

        return instance

    def get_network_categories(self):
        return [
            hou.objNodeTypeCategory()
        ]
