"""Load a camera asset in Blender."""

from openpype.hosts.blender.api import plugin


class BlendCameraLoader(plugin.AssetLoader):
    """Load a camera from a .blend file.

    Warning:
        Loading the same asset more then once is not properly supported at the
        moment.
    """

    families = ["camera"]
    representations = ["blend"]

    label = "Link Camera"
    icon = "code-fork"
    color = "orange"
    color_tag = "COLOR_05"

    maintained_parameters = [
        "parent",
        "transforms",
        "constraints",
        "targets",
        "drivers",
    ]

    def _process(self, libpath, asset_group):
        self._load_blend(libpath, asset_group)
