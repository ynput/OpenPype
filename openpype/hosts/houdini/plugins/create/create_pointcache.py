# -*- coding: utf-8 -*-
from openpype.hosts.houdini.api import plugin
from openpype.hosts.houdini.api import list_instances
from openpype.pipeline import CreatedInstance


class CreatePointCache(plugin.HoudiniCreator):
    """Alembic ROP to pointcache"""
    identifier = "pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"

    def collect_instances(self):
        for instance_data in list_instances():
            instance = CreatedInstance.from_existing(
                instance_data, self
            )
            self._add_instance_to_context(instance)

    def create(self, subset_name, instance_data, pre_create_data):
        pass

    def __init__(self, *args, **kwargs):
        super(CreatePointCache, self).__init__(*args, **kwargs)

        # Remove the active, we are checking the bypass flag of the nodes
        self.data.pop("active", None)

        self.data.update({"node_type": "alembic"})

    def _process(self, instance):
        """Creator main entry point.

        Args:
            instance (hou.Node): Created Houdini instance.

        """
        parms = {
            "use_sop_path": True,  # Export single node from SOP Path
            "build_from_path": True,  # Direct path of primitive in output
            "path_attrib": "path",  # Pass path attribute for output
            "prim_to_detail_pattern": "cbId",
            "format": 2,  # Set format to Ogawa
            "facesets": 0,  # No face sets (by default exclude them)
            "filename": "$HIP/pyblish/%s.abc" % self.name,
        }

        if self.nodes:
            node = self.nodes[0]
            parms.update({"sop_path": node.path()})

        instance.setParms(parms)
        instance.parm("trange").set(1)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        for name in to_lock:
            parm = instance.parm(name)
            parm.lock(True)
