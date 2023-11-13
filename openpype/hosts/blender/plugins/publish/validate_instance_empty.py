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
        asset_group = instance.data["instance_node"]

        if isinstance(asset_group, bpy.types.Collection):
            if not (asset_group.objects or asset_group.children):
                raise RuntimeError(f"Instance {instance.name} is empty.")
        elif isinstance(asset_group, bpy.types.Object):
            if not asset_group.children:
                raise RuntimeError(f"Instance {instance.name} is empty.")
