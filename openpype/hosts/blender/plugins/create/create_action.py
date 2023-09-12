"""Create an animation asset."""

import bpy

from openpype.pipeline import get_current_task_name, CreatedInstance
import openpype.hosts.blender.api.plugin
from openpype.hosts.blender.api import lib
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class CreateAction(openpype.hosts.blender.api.plugin.BlenderCreator):
    """Action output for character rigs"""

    identifier = "io.openpype.creators.blender.action"
    name = "actionMain"
    label = "Action"
    family = "action"
    icon = "male"

    def create(
        self, subset_name: str, instance_data: dict, pre_create_data: dict
    ):
        self._add_instance_to_context(
            CreatedInstance(self.family, subset_name, instance_data, self)
        )

        name = openpype.hosts.blender.api.plugin.asset_name(
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
                "label": self.label,
                "task": get_current_task_name(),
                "subset": subset_name,
                "instance_node": instance_node,
            }
        )
        lib.imprint(collection, instance_data)

        if pre_create_data.get("useSelection"):
            for obj in lib.get_selection():
                if (obj.animation_data is not None
                        and obj.animation_data.action is not None):

                    empty_obj = bpy.data.objects.new(name=name,
                                                     object_data=None)
                    empty_obj.animation_data_create()
                    empty_obj.animation_data.action = obj.animation_data.action
                    empty_obj.animation_data.action.name = name
                    collection.objects.link(empty_obj)

        return collection

    # Deprecated
    def process(self):

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = openpype.hosts.blender.api.plugin.asset_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = get_current_task_name()
        lib.imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            for obj in lib.get_selection():
                if (obj.animation_data is not None
                        and obj.animation_data.action is not None):

                    empty_obj = bpy.data.objects.new(name=name,
                                                     object_data=None)
                    empty_obj.animation_data_create()
                    empty_obj.animation_data.action = obj.animation_data.action
                    empty_obj.animation_data.action.name = name
                    collection.objects.link(empty_obj)

        return collection
