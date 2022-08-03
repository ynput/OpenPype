"""Load a fbx camera asset in Blender."""

from openpype.hosts.blender.api import plugin


class FbxCameraLoader(plugin.AssetLoader):
    """Import a camera from a .fbx file.

    Stores the imported asset in a collection named after the asset.
    """

    families = ["camera"]
    representations = ["fbx"]

    label = "Import Camera"
    icon = "download"
    color = "orange"
    color_tag = "COLOR_05"
    order = 4

    def _process(self, libpath, asset_group):
        self._load_fbx(libpath, asset_group)
