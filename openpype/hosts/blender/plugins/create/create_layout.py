"""Create a layout asset."""

import bpy

from openpype.hosts.blender.api import plugin, lib


class CreateLayout(plugin.BaseCreator):
    """Layout output for character rigs."""

    identifier = "io.openpype.creators.blender.layout"
    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    create_as_asset_group = True

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):

        asset_group = super().create(subset_name,
                                     instance_data,
                                     pre_create_data)

        # Add selected objects to instance
        if pre_create_data.get("use_selection"):
            bpy.context.view_layer.objects.active = asset_group
            selected = lib.get_selection()
            for obj in selected:
                obj.select_set(True)
            selected.append(asset_group)
            bpy.ops.object.parent_set(keep_transform=True)

        return asset_group
