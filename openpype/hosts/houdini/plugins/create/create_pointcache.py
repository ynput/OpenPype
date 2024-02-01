# -*- coding: utf-8 -*-
"""Creator plugin for creating pointcache alembics."""
from openpype.hosts.houdini.api import plugin
from openpype.lib import BoolDef

import hou



class CreatePointCache(plugin.HoudiniCreator):
    """Alembic ROP to pointcache"""
    identifier = "io.openpype.creators.houdini.pointcache"
    label = "PointCache (Abc)"
    family = "pointcache"
    icon = "gears"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data.pop("active", None)
        instance_data.update({"node_type": "alembic"})
        creator_attributes = instance_data.setdefault(
            "creator_attributes", dict())
        creator_attributes["farm"] = pre_create_data["farm"]

        instance = super(CreatePointCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)

        instance_node = hou.node(instance.get("instance_node"))
        parms = {
            "use_sop_path": True,
            "build_from_path": True,
            "path_attrib": "path",
            "prim_to_detail_pattern": "cbId",
            "format": 2,
            "facesets": 0,
            "filename": hou.text.expandString(
                "$HIP/pyblish/{}.abc".format(subset_name))
        }

        if self.selected_nodes:
            selected_node = self.selected_nodes[0]

            # Although Houdini allows ObjNode path on `sop_path` for the
            # the ROP node we prefer it set to the SopNode path explicitly

            # Allow sop level paths (e.g. /obj/geo1/box1)
            if isinstance(selected_node, hou.SopNode):
                parms["sop_path"] = selected_node.path()
                self.log.debug(
                   "Valid SopNode selection, 'SOP Path' in ROP will be set to '%s'."
                   % selected_node.path()
                )

            # Allow object level paths to Geometry nodes (e.g. /obj/geo1)
            # but do not allow other object level nodes types like cameras, etc.
            elif isinstance(selected_node, hou.ObjNode) and \
                    selected_node.type().name() in ["geo"]:

                # get the output node with the minimum
                # 'outputidx' or the node with display flag
                sop_path = self.get_obj_output(selected_node)

                if sop_path:
                    parms["sop_path"] = sop_path.path()
                    self.log.debug(
                        "Valid ObjNode selection, 'SOP Path' in ROP will be set to "
                        "the child path '%s'."
                        % sop_path.path()
                    )

            if not parms.get("sop_path", None):
                self.log.debug(
                    "Selection isn't valid. 'SOP Path' in ROP will be empty."
                )
        else:
            self.log.debug(
                "No Selection. 'SOP Path' in ROP will be empty."
            )

        instance_node.setParms(parms)
        instance_node.parm("trange").set(1)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        self.lock_parameters(instance_node, to_lock)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.sopNodeTypeCategory()
        ]

    def get_obj_output(self, obj_node):
        """Find output node with the smallest 'outputidx'."""

        outputs = obj_node.subnetOutputs()

        # if obj_node is empty
        if not outputs:
            return

        # if obj_node has one output child whether its
        # sop output node or a node with the render flag
        elif len(outputs) == 1:
            return outputs[0]

        # if there are more than one, then it have multiple ouput nodes
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
