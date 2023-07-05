# -*- coding: utf-8 -*-
"""Creator plugin for creating pointcache alembics."""
from openpype.hosts.houdini.api import plugin

import hou


class CreatePointCache(plugin.HoudiniCreator):
    """Alembic ROP to pointcache"""
    identifier = "io.openpype.creators.houdini.pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data.pop("active", None)
        instance_data.update({"node_type": "alembic"})

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

            # Although Houdini allows ObjNode path on `sop_path`rop node
            #  However, it's preferred to set SopNode path explicitly
            # These checks prevent using user selecting

            # Allow sop level paths (e.g. /obj/geo1/box1)
            # but do not allow other sop level paths when
            #   the parent type is not 'geo' like
            #   Cameras, Dopnet nodes(sop solver)
            if isinstance(selected_node, hou.SopNode) and \
                selected_node.parent().type().name() == 'geo':
                parms["sop_path"] = selected_node.path()
                self.log.debug(
                   "Valid SopNode selection, 'SOP Path' in ROP will be set to '%s'."
                   % selected_node.path()
                )

            # Allow object level paths to Geometry nodes (e.g. /obj/geo1)
            # but do not allow other object level nodes types like cameras, etc.
            elif isinstance(selected_node, hou.ObjNode) and \
                    selected_node.type().name() == 'geo':

                # get the output node with the minimum
                # 'outputidx' or the node with display flag
                sop_path = self.get_obj_output(selected_node) or \
                    selected_node.displayNode()

                if sop_path:
                    parms["sop_path"] = sop_path.path()
                    self.log.debug(
                        "Valid ObjNode selection, 'SOP Path' in ROP will be set to "
                        "the child path '%s'."
                        % sop_path.path()
                    )

            if not parms.get("sop_path", None):
                self.log.debug(
                "Selection isn't valid.'SOP Path' in ROP will be empty."
                )
        else:
            self.log.debug(
                "No Selection.'SOP Path' in ROP will be empty."
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

        outputs = dict()

        for sop_node in obj_node.children():
            if sop_node.type().name() == 'output' :
                outputs.update({sop_node : sop_node.parm('outputidx').eval()})

        if outputs:
            return min(outputs, key = outputs.get)
        else:
            return
