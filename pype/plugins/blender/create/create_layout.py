"""Create a layout asset."""

import bpy

from avalon import api
from avalon.blender import Creator, lib
import pype.hosts.blender.plugin


class CreateLayout(Creator):
    """Layout output for character rigs"""

    name = "layoutMain"
    label = "Layout"
    family = "layout"
    icon = "cubes"

    def process(self):

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = pype.hosts.blender.plugin.asset_name(asset, subset)
        collection = bpy.data.collections.new(name=name)
        bpy.context.scene.collection.children.link(collection)
        self.data['task'] = api.Session.get('AVALON_TASK')
        lib.imprint(collection, self.data)

        # Add the rig object and all the children meshes to
        # a set and link them all at the end to avoid duplicates.
        # Blender crashes if trying to link an object that is already linked.
        # This links automatically the children meshes if they were not
        # selected, and doesn't link them twice if they, insted,
        # were manually selected by the user.
        objects_to_link = set()

        if (self.options or {}).get("useSelection"):

            for obj in lib.get_selection():

                objects_to_link.add(obj)

                if obj.type == 'ARMATURE':

                    for subobj in obj.children:

                        objects_to_link.add(subobj)

        for obj in objects_to_link:

            collection.objects.link(obj)

        return collection
