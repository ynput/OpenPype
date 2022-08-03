"""Load a camera asset in Blender."""

from openpype.hosts.blender.api import plugin


class LinkCameraLoader(plugin.AssetLoader):
    """Link a camera from a .blend file."""

    families = ["camera"]
    representations = ["blend"]

    label = "Link Camera"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_05"
    order = 0

    maintained_parameters = [
        "parent",
        "transforms",
        "constraints",
        "targets",
        "drivers",
    ]

    def _process(self, libpath, asset_group):
        self._link_blend(libpath, asset_group)


class AppendCameraLoader(LinkCameraLoader):
    """Append a camera from a .blend file."""

    label = "Append Camera"
    icon = "paperclip"
    order = 1

    def _process(self, libpath, asset_group):
        self._append_blend(libpath, asset_group)
