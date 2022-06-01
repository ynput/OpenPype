"""Load an asset in Blender from an Alembic file."""

from openpype.hosts.blender.api import plugin


class FbxModelLoader(plugin.AssetLoader):
    """Load FBX models.

    Stores the imported asset in an empty named after the asset.
    """

    families = ["model", "rig"]
    representations = ["fbx"]

    label = "Load FBX"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_04"

    def _process(self, libpath, asset_group):
        self._load_fbx(libpath, asset_group)
