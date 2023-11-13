"""Create a Blender scene asset."""

import bpy

from openpype.pipeline import get_current_task_name
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import (
    AVALON_INSTANCES,
    AVALON_PROPERTY,
)


class CreateBlendScene(plugin.Creator):
    """Generic group of assets."""

    name = "blendScene"
    label = "Blender Scene"
    family = "blendScene"
    icon = "cubes"

    maintain_selection = False

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """Run the creator on Blender main thread."""
        mti = ops.MainThreadItem(
            self._process, subset_name, instance_data, pre_create_data
        )
        ops.execute_in_main_thread(mti)

    def _process(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        # Get Instance Container or create it if it does not exist
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if not instances:
            instances = bpy.data.collections.new(name=AVALON_INSTANCES)
            bpy.context.scene.collection.children.link(instances)

        # Create instance object
        asset = instance_data.get("asset")
        name = plugin.asset_name(asset, subset_name)

        # Create the new asset group as collection
        asset_group = bpy.data.collections.new(name=name)
        instances.children.link(asset_group)
        asset_group[AVALON_PROPERTY] = instance_node = {
            "name": asset_group.name
        }

        self.set_instance_data(subset_name, instance_data, instance_node)
        lib.imprint(asset_group, instance_data)

        if (self.options or {}).get("useSelection"):
            selection = lib.get_selection(include_collections=True)

            for data in selection:
                if isinstance(data, bpy.types.Collection):
                    asset_group.children.link(data)
                elif isinstance(data, bpy.types.Object):
                    asset_group.objects.link(data)

        return asset_group
