# -*- coding: utf-8 -*-
"""Creator plugin for creating alembic camera subsets."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance, CreatorError

import hou


class CreateAlembicCamera(plugin.HoudiniCreator):
    """Single baked camera from Alembic ROP."""

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

        instance_node = instance.transient_data["instance_node"]
        parms = {
            "filename": hou.text.expandString(
                "$HIP/pyblish/{}.abc".format(subset_name)),
            "use_sop_path": False,
        }

        if self.selected_nodes:
            if len(self.selected_nodes) > 1:
                raise CreatorError("More than one item selected.")
            path = self.selected_nodes[0].path()
            # Split the node path into the first root and the remainder
            # So we can set the root and objects parameters correctly
            _, root, remainder = path.split("/", 2)
            parms.update({"root": "/" + root, "objects": remainder})

        instance_node.setParms(parms)

        # Lock the Use Sop Path setting so the
        # user doesn't accidentally enable it.
        to_lock = ["use_sop_path"]
        self.lock_parameters(instance_node, to_lock)

        instance_node.parm("trange").set(1)

    def get_network_categories(self):
        return [
            hou.ropNodeTypeCategory(),
            hou.objNodeTypeCategory()
        ]
