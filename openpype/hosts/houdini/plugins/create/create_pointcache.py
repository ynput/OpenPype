# -*- coding: utf-8 -*-
"""Creator plugin for creating pointcache alembics."""
from openpype.hosts.houdini.api import plugin
# from openpype.pipeline import CreatedInstance

import hou


class CreatePointCache(plugin.HoudiniCreator):
    """Alembic ROP to pointcache"""
    identifier = "io.openpype.creators.houdini.pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou

        instance_data.pop("active", None)
        instance_data.update({"node_type": "alembic"})

        instance = super(CreatePointCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

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
            parent = self.selected_nodes[0]
            parms["sop_path"] = parent.path()

            child_render = ""
            child_output = ""

            # try to find output node
            for child in parent.children():
                if child.isGenericFlagSet(hou.nodeFlag.Render):
                    child_render = child
                if child.type().name() == "output":
                    child_output = child
                    break

            # create output node if not exists
            if not child_output:
                child_output = parent.createNode("output", "OUTPUT")
                child_output.setFirstInput(child_render)

                child_output.setDisplayFlag(1)
                child_output.setRenderFlag(1)
                child_output.moveToGoodPosition()

            paths = child_output.geometry().findPrimAttrib("path") and \
                      child_output.geometry().primStringAttribValues("path")

            # Create default path value if missing
            if not paths:
                path_node = parent.createNode("name", "AUTO_PATH")
                path_node.parm("attribname").set("path")
                path_node.parm("name1").set('`opname("..")`/`opoutput(".", 0)`') #noqa

                path_node.setFirstInput(child_output.input(0))
                path_node.moveToGoodPosition()
                child_output.setFirstInput(path_node)
                child_output.moveToGoodPosition()

            parms["sop_path"] = child_output.path()
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
