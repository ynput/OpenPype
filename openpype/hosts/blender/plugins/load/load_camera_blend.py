"""Load a camera asset in Blender."""

from openpype.hosts.blender.api import plugin


class CameraMaintainer(plugin.ContainerMaintainer):
    """Overloaded ContainerMaintainer to maintain only needed properties
    for camera container."""

    maintained_parameters = [
        "parent",
        "transforms",
        "constraints",
        "targets",
        "drivers",
    ]


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

    update_mainterner = CameraMaintainer

    def _process(self, libpath, asset_group):
        self._load_blend(libpath, asset_group)
