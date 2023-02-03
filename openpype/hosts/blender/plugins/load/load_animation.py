"""Load an animation in Blender."""

from typing import Dict, Optional

import bpy

from openpype.hosts.blender.api import plugin


class AnimationLoader(plugin.AssetLoader):
    """Load animations from a .blend file."""
    families = ["animation"]

    color = "orange"

    bl_types = frozenset({bpy.types.Action})


class LinkAnimationLoader(AnimationLoader):
    """Link animations from a .blend file."""
    representations = ["blend"]

    label = "Link Animation"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendAnimationLoader(AnimationLoader):
    """Append animations from a .blend file."""
    representations = ["blend"]

    label = "Append Animation"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
