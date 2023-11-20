# -*- coding: utf-8 -*-
"""Creator plugin for creating USD renders."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance

import hou


class CreateUSDRender(plugin.HoudiniCreator):
    """USD Render ROP in /stage"""
    identifier = "io.openpype.creators.houdini.usdrender"
    label = "USD Render (experimental)"
    family = "usdrender"
    icon = "magic"

    def create(self, subset_name, instance_data, pre_create_data):

        # Allow creating the
        node_type = "usdrender"
        parent = pre_create_data.get("parent")
        if parent:
            parent_node = hou.node(parent)
            if parent_node.childTypeCategory() == hou.lopNodeTypeCategory():
                node_type = "usdrender_rop"
            elif parent_node.childTypeCategory() != hou.ropNodeTypeCategory():
                raise ValueError(
                    "Unable to create USD Render instance under parent: "
                    "{}".format(parent)
                )

        instance_data["parent"] = hou.node("/stage")

        # Remove the active, we are checking the bypass flag of the nodes
        instance_data.pop("active", None)
        instance_data.update({"node_type": node_type})

        instance = super(CreateUSDRender, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))


        parms = {
            # Render frame range
            "trange": 1
        }
        if self.selected_nodes:
            parms["loppath"] = self.selected_nodes[0].path()
        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id"]
        self.lock_parameters(instance_node, to_lock)

    def get_network_categories(self):
        """Return in which network view type this creator should show.

        The node type categories returned here will be used to define where
        the creator will show up in the TAB search for nodes in Houdini's
        Network View.

        This can be overridden in inherited classes to define where that
        particular Creator should be visible in the TAB search.

        Returns:
            list: List of houdini node type categories

        """
        return [hou.ropNodeTypeCategory(), hou.lopNodeTypeCategory()]

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
        return super(CreateUSDRender, self).create_interactive(kwargs)
