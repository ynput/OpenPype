"""Create a model asset."""

import bpy

from openpype.hosts.blender.api import plugin, lib, ops

class CreateModel(plugin.BaseCreator):
    """Polygonal static geometry."""

    identifier = "io.openpype.creators.blender.model"
    name = "modelMain"
    label = "Model"
    family = "model"
    icon = "cube"

    create_as_asset_group = True

    @ops.execute_function_in_main_thread
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
