"""Create a pointcache asset."""

import bpy

from openpype.pipeline import get_current_task_name, CreatedInstance
from openpype.hosts.blender.api import plugin, lib, ops
from openpype.hosts.blender.api.pipeline import AVALON_INSTANCES
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class CreatePointcache(plugin.BaseCreator):
    """Polygonal static geometry"""

    identifier = "io.openpype.creators.blender.pointcache"
    name = "pointcacheMain"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        self._add_instance_to_context(
            CreatedInstance(self.family, subset_name, instance_data, self)
        )

        name = plugin.asset_name(
            instance_data["asset"], subset_name
        )
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)

        collection[AVALON_PROPERTY] = instance_node = {
            "name": collection.name,
        }

        instance_data.update(
            {
                "id": "pyblish.avalon.instance",
                "creator_identifier": self.identifier,
                "label": subset_name,
                "task": get_current_task_name(),
                "subset": subset_name,
                "instance_node": instance_node,
            }
        )
        lib.imprint(collection, instance_data)

        if pre_create_data.get("useSelection"):
            objects = lib.get_selection()
            for obj in objects:
                collection.objects.link(obj)
                if obj.type == 'EMPTY':
                    objects.extend(obj.children)

        return collection

    # Deprecated
    def process(self):
        """ Run the creator on Blender main thread"""
        mti = ops.MainThreadItem(self._process)
        ops.execute_in_main_thread(mti)

    def _process(self):
        # Get Instance Container or create it if it does not exist
        instances = bpy.data.collections.get(AVALON_INSTANCES)
        if not instances:
            instances = bpy.data.collections.new(name=AVALON_INSTANCES)
            bpy.context.scene.collection.children.link(instances)

        # Create instance object
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = plugin.asset_name(asset, subset)
        asset_group = bpy.data.objects.new(name=name, object_data=None)
        asset_group.empty_display_type = 'SINGLE_ARROW'
        instances.objects.link(asset_group)
        self.data['task'] = get_current_task_name()
        lib.imprint(asset_group, self.data)

        # Add selected objects to instance
        if (self.options or {}).get("useSelection"):
            bpy.context.view_layer.objects.active = asset_group
            selected = lib.get_selection()
            for obj in selected:
                if obj.parent in selected:
                    obj.select_set(False)
                    continue
            selected.append(asset_group)
            bpy.ops.object.parent_set(keep_transform=True)

        return asset_group
