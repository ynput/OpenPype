"""Load a lighting in Blender.

A lighting is a collection of light objects with combos or rigs, plus a world.
"""

import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.utils import BL_OUTLINER_TYPES

class LinkBlenderLightingLoader(plugin.AssetLoader):
    """Link lighting from a .blend file."""

    families = ["blender.lighting"]
    representations = ["blend"]

    label = "Link Blender Lighting"
    icon = "link"
    color = "orange"
    order = 0

    load_type = "LINK"

    bl_types = frozenset(BL_OUTLINER_TYPES | {bpy.types.World})


class AppendBlenderLightingLoader(LinkBlenderLightingLoader):
    """Append lighting from a .blend file."""

    families = ["blender.lighting"]
    representations = ["blend"]

    label = "Append Blender Lighting"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
