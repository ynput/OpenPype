"""Create a rig asset."""

import bpy

from openpype.pipeline import get_current_task_name, CreatedInstance
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import (
    AVALON_INSTANCES,
    AVALON_PROPERTY,
)


class CreateRig(plugin.BaseCreator):
    """Artist-friendly rig with controls to direct motion."""

    identifier = "io.openpype.creators.blender.rig"
    name = "rigMain"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

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
