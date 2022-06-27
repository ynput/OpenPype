"""Load a fbx camera asset in Blender."""

from openpype.hosts.blender.api import plugin


class FbxCameraLoader(plugin.AssetLoader):
    """Load a camera from a .fbx file.

    Stores the imported asset in a collection named after the asset.
    """

    families = ["camera"]
    representations = ["fbx"]

    label = "Load Camera"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_05"

    def _process(self, libpath, asset_group):
        self._load_fbx(libpath, asset_group)
