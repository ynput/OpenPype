# -*- coding: utf-8 -*-
"""Creator plugin for creating composite sequences."""
from openpype.hosts.houdini.api import plugin
from openpype.pipeline import CreatedInstance


class CreateCompositeSequence(plugin.HoudiniCreator):
    """Composite ROP to Image Sequence"""

    identifier = "io.openpype.creators.houdini.imagesequence"
    label = "Composite (Image Sequence)"
    family = "imagesequence"
    icon = "gears"

    def create(self, subset_name, instance_data, pre_create_data):
        import hou  # noqa

        instance_data.pop("active", None)
        instance_data.update({"node_type": "comp"})

        instance = super(CreateCompositeSequence, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        instance_node = hou.node(instance.get("instance_node"))
        filepath = "$HIP/pyblish/{}.$F4.exr".format(subset_name)
        parms = {
            "copoutput": filepath
        }

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        self.lock_parameters(instance_node, to_lock)
