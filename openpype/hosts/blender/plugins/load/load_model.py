"""Load a model asset in Blender."""

import bpy

from openpype.hosts.blender.api import plugin


class LinkModelLoader(plugin.AssetLoader):
    """Link models from a .blend file."""

    families = ["model"]
    representations = ["blend"]

    label = "Link Model"
    icon = "link"
    color = "orange"
    color_tag = "COLOR_04"
    order = 0

    load_type = "LINK"


class AppendModelLoader(plugin.AssetLoader):
    """Append models from a .blend file."""

    families = ["model"]
    representations = ["blend"]

    label = "Append Model"
    icon = "paperclip"
    color = "orange"
    color_tag = "COLOR_04"
    order = 1

    load_type = "APPEND"


class InstanceModelLoader(plugin.AssetLoader):
    """load models from a .blend file as instance collection."""

    families = ["model"]
    representations = ["blend"]

    label = "Instantiate Collection"
    icon = "archive"
    color = "orange"
    color_tag = "COLOR_04"
    order = 2

    load_type = "INSTANCE"

    def _apply_options(self, asset_group, options):
        """Apply load options fro asset_group."""

        transform = options.get("transform")
        parent = options.get("parent")

        if transform:
            location = transform.get("translation")
            rotation = transform.get("rotation")
            scale = transform.get("scale")

            asset_group.location = [location[n] for n in "xyz"]
            asset_group.rotation_euler = [rotation[n] for n in "xyz"]
            asset_group.scale = [scale[n] for n in "xyz"]

        if isinstance(parent, bpy.types.Object):
            with plugin.context_override(active=parent, selected=asset_group):
                bpy.ops.object.parent_set(keep_transform=True)
        elif isinstance(parent, bpy.types.Collection):
            for current_parent in asset_group.users_collection:
                current_parent.children.unlink(asset_group)
            plugin.link_to_collection(asset_group, parent)
