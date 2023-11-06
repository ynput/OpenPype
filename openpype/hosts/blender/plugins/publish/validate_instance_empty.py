import bpy

import pyblish.api


class ValidateInstanceEmpty(pyblish.api.InstancePlugin):
    """Validator to verify that the instance is not empty"""

    order = pyblish.api.ValidatorOrder - 0.01
    hosts = ["blender"]
    families = ["blendScene"]
    label = "Validate Instance is not Empty"
    optional = False

    def process(self, instance):
        collection = bpy.data.collections[instance.name]
        if not (collection.objects or collection.children):
            raise RuntimeError(f"Instance {instance.name} is empty.")
