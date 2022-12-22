"""Load and assign extracted nodegroups."""

import bpy

from openpype.hosts.blender.api import plugin


class BlenderNodegroupLoader(plugin.AssetLoader):
    """Load and assign extracted nodegroups from .blend file."""

    representations = ["blend"]

    color = "orange"
    no_namespace = True

    bl_types = frozenset({bpy.types.GeometryNodeTree, bpy.types.Object})

    def update(self, *args, **kwargs):
        """Override `update` to restore updated nodegroups into modifiers."""
        # Keep used nodegroups in modifiers
        modifiers_users = {}
        for o in bpy.data.objects:
            modifiers_users.update(
                {
                    m.node_group.name: m
                    for m in o.modifiers
                    if m.type == "NODES"
                }
            )

        # Update datablocks
        container, datablocks = super().update(*args, **kwargs)

        # Set nodegroups back in modifiers
        for n in bpy.data.node_groups:
            modifier = modifiers_users.get(n.name)
            if modifier and modifier.node_group != n:
                modifier.node_group = n

        return container, datablocks


class LinkBlenderNodegroupLoader(BlenderNodegroupLoader):
    """Link nodegroups from a .blend file."""

    families = ["blender.nodegroup"]

    label = "Link Nodegroup"
    icon = "link"
    order = 0

    load_type = "LINK"


class AppendBlenderNodegroupLoader(BlenderNodegroupLoader):
    """Append nodegroups from a .blend file."""

    families = ["blender.nodegroup"]

    label = "Append Nodegroup"
    icon = "paperclip"
    order = 1

    load_type = "APPEND"
