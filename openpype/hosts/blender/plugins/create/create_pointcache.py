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
