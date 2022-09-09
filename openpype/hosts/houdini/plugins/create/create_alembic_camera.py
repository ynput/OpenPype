# -*- coding: utf-8 -*-
"""Creator plugin for creating alembic camera subsets."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


class CreateAlembicCamera(plugin.HoudiniCreator):
    """Single baked camera from Alembic ROP"""

    identifier = "io.openpype.creators.houdini.camera"
    label = "Camera (Abc)"
    family = "camera"
    icon = "camera"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou

        instance_data.pop("active", None)
        instance_data.update({"node_type": "alembic"})

        instance = super(CreateAlembicCamera, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))
        parms = {
            "filename": "$HIP/pyblish/{}.abc".format(subset_name),
            "use_sop_path": False,
        }

        if self.selected_nodes:
            path = self.selected_nodes.path()
            # Split the node path into the first root and the remainder
            # So we can set the root and objects parameters correctly
            _, root, remainder = path.split("/", 2)
            parms.update({"root": "/" + root, "objects": remainder})

        instance_node.setParms(parms)

        # Lock the Use Sop Path setting so the
        # user doesn't accidentally enable it.
        instance_node.parm("use_sop_path").lock(True)
        instance_node.parm("trange").set(1)
