"""Load an asset in Blender from a FBX file."""

import bpy

from openpype.hosts.blender.api import plugin


class FbxModelLoader(plugin.AssetLoader):
    """Import FBX models.

    Stores the imported asset in a collection named after the asset.
    """

    families = ["model", "rig"]
    representations = ["fbx"]

    label = "Import FBX"
    icon = "download"
    color = "orange"
    color_tag = "COLOR_04"
    order = 4

    scale_length = 0

    def _load_process(self, libpath, container_name):  # TODO

        kept_scale_length = bpy.context.scene.unit_settings.scale_length
        if self.scale_length > 0:
            bpy.context.scene.unit_settings.scale_length = self.scale_length

        bpy.context.scene.unit_settings.scale_length = kept_scale_length
        
        return self._load_fbx(libpath, container_name)
