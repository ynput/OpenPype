"""Load an asset in Blender from a FBX file."""

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

    def _process(self, libpath, asset_group):
        self._load_fbx(libpath, asset_group)
