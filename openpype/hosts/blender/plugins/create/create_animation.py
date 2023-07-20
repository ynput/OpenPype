"""Create an animation asset."""

import bpy

from openpype.pipeline import get_current_task_name, CreatedInstance
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES


class CreateAnimation(plugin.BlenderCreator):
    """Animation output for character rigs"""

    identifier = "io.openpype.creators.blender.animation"
    name = "animationMain"
    label = "Animation"
    family = "animation"
    icon = "male"

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        """ Run the creator on Blender main thread"""
        self._add_instance_to_context(
            CreatedInstance(self.family, subset_name, instance_data, self)
        )

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
        # name = self.name
        # if not name:
        name = plugin.asset_name(instance_data["asset"], subset_name)
        # asset_group = bpy.data.objects.new(name=name, object_data=None)
        # asset_group.empty_display_type = 'SINGLE_ARROW'
        asset_group = bpy.data.collections.new(name=name)
        instances.children.link(asset_group)
        instance_data.update(
            {
                "id": "pyblish.avalon.instance",
                "creator_identifier": self.identifier,
                "label": self.label,
                "task": get_current_task_name(),
                "subset": subset_name,
            }
        )
        lib.imprint(asset_group, instance_data)

        if pre_create_data.get("useSelection"):
            selected = lib.get_selection()
            for obj in selected:
                asset_group.objects.link(obj)
        elif pre_create_data.get("asset_group"):
            obj = (self.options or {}).get("asset_group")
            asset_group.objects.link(obj)

        return asset_group

    # Deprecated
    def process(self):
        """ Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process_legacy)
        ops.execute_in_main_thread(mti)

    # Deprecated
    def _process_legacy(self):
        # Get Instance Container or create it if it does not exist
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if not instances:
            instances = bpy.data.collections.new(name=AVALON_INSTANCES)
            bpy.context.scene.collection.children.link(instances)

        # Create instance object
        # name = self.name
        # if not name:
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)
        # asset_group = bpy.data.objects.new(name=name, object_data=None)
        # asset_group.empty_display_type = 'SINGLE_ARROW'
        asset_group = bpy.data.collections.new(name=name)
        instances.children.link(asset_group)
        self.data['task'] = get_current_task_name()
        lib.imprint(asset_group, self.data)

        if (self.options or {}).get("useSelection"):
            selected = lib.get_selection()
            for obj in selected:
                asset_group.objects.link(obj)
        elif (self.options or {}).get("asset_group"):
            obj = (self.options or {}).get("asset_group")
            asset_group.objects.link(obj)

        return asset_group
