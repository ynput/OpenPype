"""Create a camera asset."""

import bpy

from avalon import api
from avalon.blender import Creator, lib
import pype.hosts.blender.plugin


class CreateCamera(Creator):
    """Polygonal static geometry"""

    name = "cameraMain"
    label = "Camera"
    family = "camera"
    icon = "video-camera"

    def process(self):

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = pype.hosts.blender.plugin.asset_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = api.Session.get('AVALON_TASK')
        lib.imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            for obj in lib.get_selection():
                collection.objects.link(obj)

        return collection
