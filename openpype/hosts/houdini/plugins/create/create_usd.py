# -*- coding: utf-8 -*-
"""Creator plugin for creating USDs."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance

import hou


class CreateUSD(plugin.HoudiniCreator):
    """Universal Scene Description"""
    identifier = "io.openpype.creators.houdini.usd"
    label = "USD (experimental)"
    family = "usd"
    icon = "gears"
    enabled = False

    def create(self, subset_name, instance_data, pre_create_data):

        # Allow creating the USD node directly in a LOP network as opposed
        # to an /out network by defining the type based on a `parent` if
        # it passed along.
        node_type = "usd"
        parent = pre_create_data.get("parent")
        if parent:
            parent_node = hou.node(parent)
            if parent_node.childTypeCategory() == hou.lopNodeTypeCategory():
                node_type = "usd_rop"
            elif parent_node.childTypeCategory() != hou.ropNodeTypeCategory():
                raise ValueError(
                    "Unable to create USD Render instance under parent: "
                    "{}".format(parent)
                )

        instance_data.pop("active", None)
        instance_data.update({"node_type": node_type})

        instance = super(CreateUSD, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            "lopoutput": "$HIP/pyblish/{}.usd".format(subset_name),
            "enableoutputprocessor_simplerelativepaths": False,
        }

        if self.selected_nodes:
            parms["loppath"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = [
            "fileperframe",
            # Lock some Avalon attributes
            "family",
            "id",
        ]
        self.lock_parameters(instance_node, to_lock)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.lopNodeTypeCategory()
        ]

    def create_interactive(self, kwargs):
        # Allow to create a USD render rop directly in LOP networks natively
        import stateutils
        from openpype.hosts.houdini.api.creator_node_shelves import (
            prompt_variant
        )

        context = self.create_context
        pane = stateutils.activePane(kwargs)
        if isinstance(pane, hou.NetworkEditor):
            pwd = pane.pwd()
            if pwd.childTypeCategory() == hou.lopNodeTypeCategory():
                # Allow to create the ROP node parented under this
                variant = prompt_variant(creator=self)
                context.create(
                    creator_identifier=self.identifier,
                    variant=variant,
                    pre_create_data={"use_selection": False,
                                     "parent": pwd.path()}
                )
                return

        # Fall back to default behavior
        return super(CreateUSD, self).create_interactive(kwargs)
