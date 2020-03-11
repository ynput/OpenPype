"""Create a rig asset."""

import bpy

from avalon import api
from avalon.blender import Creator, lib


class CreateRig(Creator):
    """Artist-friendly rig with controls to direct motion"""

    name = "rigMain"
    label = "Rig"
    family = "rig"
    icon = "wheelchair"

    # @staticmethod
    # def _find_layer_collection(self, layer_collection, collection):

    #     found = None

    #     if (layer_collection.collection == collection):

    #         return layer_collection

    #     for layer in layer_collection.children:

    #         found = self._find_layer_collection(layer, collection)

    #         if found:

    #             return found

    def process(self):
        import pype.blender

        asset = self.data["asset"]
        subset = self.data["subset"]
        name = pype.blender.plugin.asset_name(asset, subset)
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

                objects_to_link.add( obj )

                if obj.type == 'ARMATURE':

                    for subobj in obj.children:

                        objects_to_link.add( subobj )

                    # Create a new collection and link the widgets that
                    # the rig uses.
                    # custom_shapes = set()

                    # for posebone in obj.pose.bones:

                    #     if posebone.custom_shape is not None:

                    #         custom_shapes.add( posebone.custom_shape )

                    # if len( custom_shapes ) > 0:

                    #     widgets_collection = bpy.data.collections.new(name="Widgets")
                        
                    #     collection.children.link(widgets_collection)

                    #     for custom_shape in custom_shapes:

                    #         widgets_collection.objects.link( custom_shape )

                    #     layer_collection = self._find_layer_collection(bpy.context.view_layer.layer_collection, widgets_collection)

                    #     layer_collection.exclude = True

        for obj in objects_to_link:

            collection.objects.link(obj)

        return collection
