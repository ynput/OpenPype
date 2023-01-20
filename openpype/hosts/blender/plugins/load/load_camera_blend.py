"""Load a camera asset in Blender."""

from openpype.hosts.blender.api import plugin


class LinkCameraLoader(plugin.AssetLoader):
    """Link a camera from a .blend file."""

    families = ["camera"]
    representations = ["blend"]

    label = "Link Camera"
    icon = "link"
    color = "orange"
    order = 0

    load_type = "LINK"


class AppendCameraLoader(LinkCameraLoader):
    """Append a camera from a .blend file."""

    label = "Append Camera"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
