# -*- coding: utf-8 -*-
"""Creator plugin for creating pointcache alembics."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


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
            "filename": "$HIP/pyblish/{}.abc".format(subset_name)
        }

        if self.selected_nodes:
            parms["sop_path"] = self.selected_nodes[0].path()

        instance_node.setParms(parms)
        instance_node.parm("trange").set(1)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        for name in to_lock:
            parm = instance_node.parm(name)
            parm.lock(True)
