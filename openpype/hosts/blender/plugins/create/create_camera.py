"""Create a camera asset."""

import bpy

from openpype.pipeline import CreatedInstance
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import (
    AVALON_INSTANCES,
    AVALON_PROPERTY,
)


class CreateCamera(plugin.BaseCreator):
    """Polygonal static geometry."""

    identifier = "io.openpype.creators.blender.camera"
    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

    create_as_asset_group = True

    @ops.execute_function_in_main_thread
    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """Run the creator on Blender main thread."""

        asset_group = super().create(subset_name,
                                     instance_data,
                                     pre_create_data)

        if pre_create_data.get("use_selection"):
            bpy.context.view_layer.objects.active = asset_group
            selected = lib.get_selection()
            for obj in selected:
                obj.select_set(True)
            selected.append(asset_group)
            bpy.ops.object.parent_set(keep_transform=True)
        else:
            plugin.deselect_all()
            camera = bpy.data.cameras.new(subset_name)
            camera_obj = bpy.data.objects.new(subset_name, camera)

            instances = bpy.data.collections.get(AVALON_INSTANCES)
            instances.objects.link(camera_obj)

            camera_obj.select_set(True)
            asset_group.select_set(True)
            bpy.context.view_layer.objects.active = asset_group
            bpy.ops.object.parent_set(keep_transform=True)

        return asset_group
