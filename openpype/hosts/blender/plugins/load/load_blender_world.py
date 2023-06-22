"""Load a world in Blender."""

import bpy

from openpype.hosts.blender.api import plugin

class LinkBlenderWorldLoader(plugin.AssetLoader):
    """Link worlds from a .blend file."""

    families = ["blender.world"]
    representations = ["blend"]

    label = "Link Blender World"
    icon = "link"
    color = "orange"
    order = 0

    load_type = "LINK"

    bl_types = frozenset({bpy.types.World})


class AppendBlenderWorldLoader(plugin.AssetLoader):
    """Append worlds from a .blend file."""

    families = ["blender.world"]
    representations = ["blend"]

    label = "Append Blender World"
    icon = "paperclip"
    color = "orange"
    order = 1

    load_type = "APPEND"

    bl_types = frozenset({bpy.types.World})
