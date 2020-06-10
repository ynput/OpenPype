"""Create a rig asset."""

import bpy

from avalon import api
from avalon.blender import Creator, lib
import pype.hosts.blender.plugin


class CreateRig(Creator):
    """Artist-friendly rig with controls to direct motion"""

    name = "rigMain"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

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

        if (self.options or {}).get("useSelection"):
            for obj in lib.get_selection():
                for child in obj.users_collection[0].children:
                    collection.children.link(child)
                collection.objects.link(obj)

        return collection
