"""Create an animation asset."""

import bpy

from avalon import api
from avalon.blender import Creator, lib
import pype.blender.plugin


class CreateAction(Creator):
    """Action output for character rigs"""

    name = "actionMain"
    label = "Action"
    family = "action"
    icon = "male"

    def process(self):

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = pype.blender.plugin.asset_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = api.Session.get('AVALON_TASK')
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
