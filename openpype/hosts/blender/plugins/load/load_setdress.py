"""Load a setdress in Blender."""

from openpype.hosts.blender.api import plugin


class BlendSetdressLoader(plugin.AssetLoader):
    """Load setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Link SetDress"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_06"

    def _process(self, libpath, asset_group):
        self._load_blend(libpath, asset_group)
