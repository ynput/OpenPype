"""Create a model asset."""

import bpy

from avalon import api
from avalon.blender import Creator, lib


class CreateModel(Creator):
    """Polygonal static geometry"""

    name = "model_default"
    label = "Model"
    family = "model"
    icon = "cube"

    def process(self):
        import sonar.blender
        asset = self.data["asset"]
        subset = self.data["subset"]
        name = sonar.blender.plugin.model_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = api.Session.get('AVALON_TASK')
        lib.imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            for obj in bpy.context.selected_objects:
                collection.objects.link(obj)

        if bpy.data.workspaces.get('Modeling'):
            bpy.context.window.workspace = bpy.data.workspaces['Modeling']

        return collection
