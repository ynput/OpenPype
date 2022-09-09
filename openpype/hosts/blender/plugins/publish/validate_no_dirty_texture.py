from typing import List

import bpy
import pyblish.api
from openpype.api import ValidateContentsOrder
from openpype.hosts.blender.api.action import SaveDirtyTextures

class ValidateNoDirtyTexture(pyblish.api.InstancePlugin):
    """Validates that there are no dirty textures
    """

    order = ValidateContentsOrder
    hosts = ["blender"]
    families = ["look"]
    label = "Validate No Dirty Textures"
    actions = [SaveDirtyTextures]

    @staticmethod
    def get_invalid(instance) -> List:
        invalid = []
        for obj in set(instance):
            if isinstance(obj, bpy.types.Object):
                # Getting texture images
                for m in obj.material_slots:
                    images = m.material.texture_paint_images
                    if images:
                        for v in images:
                            # Checking if the image is dirty
                            if v.is_dirty:
                                invalid.append(v)

        return invalid
    
    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Dirty textures found:"
                f"{invalid}"
            )
