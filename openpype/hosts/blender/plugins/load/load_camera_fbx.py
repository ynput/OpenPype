"""Load an asset in Blender from an Alembic file."""

from openpype.hosts.blender.api import plugin


class FbxCameraLoader(plugin.AssetLoader):
    """Load a camera from FBX.

    Stores the imported asset in an empty named after the asset.
    """

    families = ["camera"]
    representations = ["fbx"]

    label = "Load Camera (FBX)"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_05"

    def _process(self, libpath, asset_group):
        self._load_fbx(libpath, asset_group)
