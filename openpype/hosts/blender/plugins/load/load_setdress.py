"""Load a setdress in Blender."""

from openpype.hosts.blender.api import plugin


class LinkSetdressLoader(plugin.AssetLoader):
    """Link setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Link SetDress"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_06"
    order = 0

    def _process(self, libpath, asset_group):
        self._link_blend(libpath, asset_group)


class AppendSetdressLoader(plugin.AssetLoader):
    """Append setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Append SetDress"
    icon = "paperclip"
    color = "orange"
    color_tag = "COLOR_06"
    order = 1

    def _process(self, libpath, asset_group):
        self._append_blend(libpath, asset_group)
