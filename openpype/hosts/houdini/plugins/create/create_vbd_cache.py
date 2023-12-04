# -*- coding: utf-8 -*-
"""Creator plugin for creating VDB Caches."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance
from openpype.lib import BoolDef

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
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        creator_attributes["farm"] = pre_create_data["farm"]
        instance = super(CreateVDBCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))
        file_path = "{}{}".format(
            hou.text.expandString("$HIP/pyblish/"),
            "{}.$F4.vdb".format(subset_name))
        parms = {
            "sopoutput": file_path,
            "initsim": True,
            "trange": 1
        }

        if self.selected_nodes:
            parms["soppath"] = self.get_sop_node_path(self.selected_nodes[0])

        instance_node.setParms(parms)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.objNodeTypeCategory(),
            hou.sopNodeTypeCategory()
        ]

    def get_sop_node_path(self, selected_node):
        """Get Sop Path of the selected node.

        Although Houdini allows ObjNode path on `sop_path` for the
        the ROP node, we prefer it set to the SopNode path explicitly.
        """

        # Allow sop level paths (e.g. /obj/geo1/box1)
        if isinstance(selected_node, hou.SopNode):
            self.log.debug(
                "Valid SopNode selection, 'SOP Path' in ROP will"
                " be set to '%s'.", selected_node.path()
            )
            return selected_node.path()

        # Allow object level paths to Geometry nodes (e.g. /obj/geo1)
        # but do not allow other object level nodes types like cameras, etc.
        elif isinstance(selected_node, hou.ObjNode) and \
                selected_node.type().name() == "geo":

            # Try to find output node.
            sop_node = self.get_obj_output(selected_node)
            if sop_node:
                self.log.debug(
                    "Valid ObjNode selection, 'SOP Path' in ROP will "
                    "be set to the child path '%s'.", sop_node.path()
                )
                return sop_node.path()

        self.log.debug(
            "Selection isn't valid. 'SOP Path' in ROP will be empty."
        )
        return ""

    def get_obj_output(self, obj_node):
        """Try to find output node.

        If any output nodes are present, return the output node with
          the minimum 'outputidx'
        If no output nodes are present, return the node with display flag
        If no nodes are present at all, return None
        """

        outputs = obj_node.subnetOutputs()

        # if obj_node is empty
        if not outputs:
            return

        # if obj_node has one output child whether its
        # sop output node or a node with the render flag
        elif len(outputs) == 1:
            return outputs[0]

        # if there are more than one, then it has multiple output nodes
        # return the one with the minimum 'outputidx'
        else:
            return min(outputs,
                       key=lambda node: node.evalParm('outputidx'))

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
