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
        import hou
        from pprint import pformat

        instance_data.pop("active", None)
        instance_data.update({"node_type": "comp"})

        instance = super(CreateCompositeSequence, self).create(
            subset_name,
            instance_data,
            pre_create_data)  # type: CreatedInstance

        self.log.info(pformat(instance))
        print(pformat(instance))
        instance_node = hou.node(instance.get("instance_node"))

        filepath = "$HIP/pyblish/{}.$F4.exr".format(subset_name)
        parms = {
            "copoutput": filepath
        }

        instance_node.setParms(parms)

        # Lock any parameters in this list
        to_lock = ["prim_to_detail_pattern"]
        for name in to_lock:
            parm = instance_node.parm(name)
            parm.lock(True)

