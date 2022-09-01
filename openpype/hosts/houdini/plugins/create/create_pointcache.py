# -*- coding: utf-8 -*-
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance

import hou


class CreatePointCache(plugin.HoudiniCreator):
    """Alembic ROP to pointcache"""
    identifier = "pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data.pop("active", None)
        instance_data.update({"node_type": "alembic"})

        instance = super(CreatePointCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("members")[0])
        parms = {
            "use_sop_path": True,
            "build_from_path": True,
            "path_attrib": "path",
            "prim_to_detail_pattern": "cbId",
            "format": 2,
            "facesets": 0,
            "filename": "$HIP/pyblish/{}.abc".format(self.identifier)
        }

        if instance_node:
            parms["sop_path"] = instance_node.path()

        instance_node.setParms(parms)
        instance_node.parm("trange").set(1)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        for name in to_lock:
            parm = instance_node.parm(name)
            parm.lock(True)
