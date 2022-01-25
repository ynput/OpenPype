"""Create a pointcache asset."""

import bpy

from avalon import api
import openpype.hosts.blender.api.plugin
from openpype.hosts.blender.api import lib


class CreatePointcache(openpype.hosts.blender.api.plugin.Creator):
    """Polygonal static geometry"""

    name = "pointcacheMain"
    label = "Point Cache"
    family = "pointcache"
    icon = "gears"

    def process(self):

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = openpype.hosts.blender.api.plugin.asset_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = api.Session.get('AVALON_TASK')
        lib.imprint(collection, self.data)

        if (self.options or {}).get("useSelection"):
            objects = lib.get_selection()
            for obj in objects:
                collection.objects.link(obj)
                if obj.type == 'EMPTY':
                    objects.extend(obj.children)

        return collection
