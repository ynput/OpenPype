"""Load a workfile in Blender."""
from itertools import chain
import bpy

from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH


class WorkfileLoader(plugin.AssetLoader):
    """Load Workfile from a .blend file."""

    bl_types = frozenset(BL_TYPE_DATAPATH.keys())  # All available types

    def load(self, *args, **kwargs):
        container, datablocks = super().load(*args, **kwargs)

        # Extract orphan datablocks
        orphan_datablocks = set(
            chain.from_iterable(
                (
                    c.all_objects
                    for c in datablocks
                    if isinstance(c, bpy.types.Collection)
                )
            )
        )
        orphan_datablocks.update(
            chain.from_iterable(
                (
                    c.children_recursive
                    for c in datablocks
                    if isinstance(c, (bpy.types.Collection, bpy.types.Object))
                )
            )
        )
        orphan_datablocks = set(datablocks) - orphan_datablocks

        # Link orphan datablocks to main collection
        plugin.link_to_collection(
            orphan_datablocks, bpy.context.scene.collection
        )

        return container, datablocks


class LinkWorkfileLoader(WorkfileLoader):
    """Link Workfile from a .blend file."""

    families = ["workfile"]
    representations = ["blend"]

    label = "Link Workfile"
    icon = "link"
    color = "orange"
    order = 0

    load_type = "LINK"


class AppendWorkfileLoader(WorkfileLoader):
    """Append Workfile from a .blend file."""

    families = ["workfile"]
    representations = ["blend"]

    label = "Append Workfile"
    icon = "paperclip"
    color = "orange"
    order = 1

    load_type = "APPEND"
