# -*- coding: utf-8 -*-
"""Creator plugin for creating VDB Caches."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance

import hou


class CreateVDBCache(plugin.HoudiniCreator):
    """OpenVDB from Geometry ROP"""
    identifier = "io.openpype.creators.houdini.vdbcache"
    name = "vbdcache"
    label = "VDB Cache"
    family = "vdbcache"
    icon = "cloud"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou

        instance_data.pop("active", None)
        instance_data.update({"node_type": "geometry"})

        instance = super(CreateVDBCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))
        parms = {
            "sopoutput": "$HIP/pyblish/{}.$F4.vdb".format(subset_name),
            "initsim": True,
            "trange": 1
        }

        if self.selected_nodes:
            parms["soppath"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.sopNodeTypeCategory()
        ]
