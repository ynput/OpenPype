# -*- coding: utf-8 -*-
"""Creator plugin for creating USD renders."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


class CreateUSDRender(plugin.HoudiniCreator):
    """USD Render ROP in /stage"""
    identifier = "io.openpype.creators.houdini.usdrender"
    label = "USD Render (experimental)"
    family = "usdrender"
    icon = "magic"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data["parent"] = hou.node("/stage")

        # Remove the active, we are checking the bypass flag of the nodes
        instance_data.pop("active", None)
        instance_data.update({"node_type": "usdrender"})

        instance = super(CreateUSDRender, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = instance.transient_data["instance_node"]


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
