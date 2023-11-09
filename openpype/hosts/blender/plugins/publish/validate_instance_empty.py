import bpy

import pyblish.api


class ValidateInstanceEmpty(pyblish.api.InstancePlugin):
    """Validator to verify that the instance is not empty"""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["model", "pointcache", "rig", "camera" "layout", "blendScene"]
    label = "Validate Instance is not Empty"
    optional = False

    def process(self, instance):
        self.log.debug(instance)
        self.log.debug(instance.data)
        if instance.data["family"] == "blendScene":
            # blendScene instances are collections
            collection = bpy.data.collections[instance.name]
            if not (collection.objects or collection.children):
                raise RuntimeError(f"Instance {instance.name} is empty.")
        else:
            # All other instances are objects
            asset_group = bpy.data.objects[instance.name]
            if not asset_group.children:
                raise RuntimeError(f"Instance {instance.name} is empty.")
