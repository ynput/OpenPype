import bpy

from avalon import api, blender
import openpype.hosts.blender.api.plugin


class CreateSetDress(openpype.hosts.blender.api.plugin.Creator):
    """A grouped package of loaded content"""

    name = "setdressMain"
    label = "Set Dress"
    family = "setdress"
    icon = "cubes"
    defaults = ["Main", "Anim"]

    def process(self):
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = openpype.hosts.blender.api.plugin.asset_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = api.Session.get('AVALON_TASK')
        blender.lib.imprint(collection, self.data)

        return collection
