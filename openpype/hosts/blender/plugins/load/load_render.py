"""Load a render scene in Blender."""

from openpype.hosts.blender.api import plugin


class LinkRenderLoader(plugin.AssetLoader):
    """Link render scenes from a .blend file."""

    families = ["render"]
    representations = ["blend"]

    label = "Link Render"
    icon = "link"
    color = "orange"
    order = 0
    no_namespace = True

    load_type = "LINK"


class AppendRenderLoader(plugin.AssetLoader):
    """Append render scenes from a .blend file."""

    families = ["render"]
    representations = ["blend"]

    label = "Append Render"
    icon = "paperclip"
    color = "orange"
    order = 1
    no_namespace = True

    load_type = "LINK"
