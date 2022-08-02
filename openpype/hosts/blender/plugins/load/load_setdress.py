"""Load a setdress in Blender."""

from openpype.hosts.blender.api import plugin


class LinkBlendSetdressLoader(plugin.AssetLoader):
    """Link setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Link SetDress"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_06"

    def _process(self, libpath, asset_group):
        self._link_blend(libpath, asset_group)


class AppendBlendSetdressLoader(plugin.AssetLoader):
    """Append setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Append SetDress"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_06"

    def _process(self, libpath, asset_group):
        self._append_blend(libpath, asset_group)
