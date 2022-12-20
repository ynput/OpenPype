"""Load a setdress in Blender."""

from openpype.hosts.blender.api import plugin


class LinkSetdressLoader(plugin.AssetLoader):
    """Link setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Link SetDress"
    icon = "link"
    color = "orange"
    order = 0

    load_type = "LINK"


class AppendSetdressLoader(plugin.AssetLoader):
    """Append setdress from a .blend file."""

    families = ["setdress"]
    representations = ["blend"]

    label = "Append SetDress"
    icon = "paperclip"
    color = "orange"
    order = 1

    load_type = "APPEND"
