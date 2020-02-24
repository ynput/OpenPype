import os
import avalon.blender.workio

import pype.api

import bpy
import bpy_extras
import bpy_extras.anim_utils


class ExtractAnimationFBX(pype.api.Extractor):
    """Extract as animation."""

    label = "Extract FBX"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.fbx"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        collections = [obj for obj in instance if type(obj) is bpy.types.Collection]

        assert len(collections) == 1, "There should be one and only one collection collected for this asset"

        old_active_layer_collection = bpy.context.view_layer.active_layer_collection

        # Get the layer collection from the collection we need to export.
        # This is needed because in Blender you can only set the active 
        # collection with the layer collection, and there is no way to get
        # the layer collection from the collection (but there is the vice versa).
        layer_collections = [layer for layer in bpy.context.view_layer.layer_collection.children if layer.collection == collections[0]]

        assert len(layer_collections) == 1

        bpy.context.view_layer.active_layer_collection = layer_collections[0]

        old_scale = bpy.context.scene.unit_settings.scale_length

        # We set the scale of the scene for the export
        bpy.context.scene.unit_settings.scale_length = 0.01

        # We export all the objects in the collection
        objects_to_export = collections[0].objects

        object_action_pairs = []
        original_actions = []

        starting_frames = []
        ending_frames = []

        # For each object, we make a copy of the current action
        for obj in objects_to_export:

            curr_action = obj.animation_data.action
            copy_action = curr_action.copy()

            object_action_pairs.append((obj, copy_action))
            original_actions.append(curr_action)

            curr_frame_range = curr_action.frame_range

            starting_frames.append( curr_frame_range[0] )
            ending_frames.append( curr_frame_range[1] )

        # We compute the starting and ending frames
        max_frame = min( starting_frames )
        min_frame = max( ending_frames )

        # We bake the copy of the current action for each object
        bpy_extras.anim_utils.bake_action_objects(
            object_action_pairs,
            frames=range(int(min_frame), int(max_frame)),
            do_object=False,
            do_clean=False
        )

        # We export the fbx
        bpy.ops.export_scene.fbx(
            filepath=filepath,
            use_active_collection=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            add_leaf_bones=False
        )

        bpy.context.view_layer.active_layer_collection = old_active_layer_collection

        bpy.context.scene.unit_settings.scale_length = old_scale

        # We delete the baked action and set the original one back
        for i in range(0, len(object_action_pairs)):

            object_action_pairs[i][0].animation_data.action = original_actions[i]

            object_action_pairs[i][1].user_clear()
            bpy.data.actions.remove(object_action_pairs[i][1])

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
