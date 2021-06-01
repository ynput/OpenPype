"""Create a layout asset."""

import bpy

from avalon import api
from avalon.blender import lib
import openpype.hosts.blender.api.plugin


class CreateLayout(openpype.hosts.blender.api.plugin.Creator):
    """Layout output for character rigs"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    def process(self):

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = openpype.hosts.blender.api.plugin.asset_name(asset, subset)
        collection = bpy.context.collection
        collection.name = name
        self.data['task'] = api.Session.get('AVALON_TASK')
        lib.imprint(collection, self.data)

        return collection
