import bpy

import pyblish.api


class ValidateRenderCameraIsSet(pyblish.api.InstancePlugin):
    """Validate that there is a camera set as active for rendering."""

    order = pyblish.api.ValidatorOrder
    hosts = ["blender"]
    families = ["render"]
    label = "Validate Render Camera Is Set"
    optional = False

    def process(self, instance):
        if not bpy.context.scene.camera:
            raise RuntimeError("No camera is active for rendering.")
