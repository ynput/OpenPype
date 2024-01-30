# -*- coding: utf-8 -*-
"""Creator plugin for creating Redshift proxies."""
from openpype.hosts.houdini.api import plugin
import hou
from openpype.lib import BoolDef


class CreateRedshiftProxy(plugin.HoudiniCreator):
    """Redshift Proxy"""
    identifier = "io.openpype.creators.houdini.redshiftproxy"
    label = "Redshift Proxy"
    family = "redshiftproxy"
    icon = "magic"

    def create(self, subset_name, instance_data, pre_create_data):

        # Remove the active, we are checking the bypass flag of the nodes
        instance_data.pop("active", None)

        # Redshift provides a `Redshift_Proxy_Output` node type which shows
        # a limited set of parameters by default and is set to extract a
        # Redshift Proxy. However when "imprinting" extra parameters needed
        # for OpenPype it starts showing all its parameters again. It's unclear
        # why this happens.
        # TODO: Somehow enforce so that it only shows the original limited
        #       attributes of the Redshift_Proxy_Output node type
        instance_data.update({"node_type": "Redshift_Proxy_Output"})
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        creator_attributes["farm"] = pre_create_data["farm"]

        instance = super(CreateRedshiftProxy, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))

        parms = {
            "RS_archive_file": '$HIP/pyblish/{}.$F4.rs'.format(subset_name),
        }

        if self.selected_nodes:
            parms["RS_archive_sopPath"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)

        # Lock some Avalon attributes
        to_lock = ["family", "id", "prim_to_detail_pattern"]
        self.lock_parameters(instance_node, to_lock)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.sopNodeTypeCategory()
        ]

    def get_instance_attr_defs(self):
        return [
            BoolDef("farm",
                    label="Submitting to Farm",
                    default=False)
        ]

    def get_pre_create_attr_defs(self):
        attrs = super().get_pre_create_attr_defs()
        # Use same attributes as for instance attributes
        return attrs + self.get_instance_attr_defs()
