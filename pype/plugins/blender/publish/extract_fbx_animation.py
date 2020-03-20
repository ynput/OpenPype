import os

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

        context = bpy.context
        scene = context.scene
        view_layer = context.view_layer

        # Perform extraction
        self.log.info("Performing extraction..")

        collections = [
            obj for obj in instance if type(obj) is bpy.types.Collection]

        assert len(collections) == 1, "There should be one and only one " \
            "collection collected for this asset"

        old_active_layer_collection = view_layer.active_layer_collection

        layers = view_layer.layer_collection.children

        # Get the layer collection from the collection we need to export.
        # This is needed because in Blender you can only set the active
        # collection with the layer collection, and there is no way to get
        # the layer collection from the collection
        # (but there is the vice versa).
        layer_collections = [
            layer for layer in layers if layer.collection == collections[0]]

        assert len(layer_collections) == 1

        view_layer.active_layer_collection = layer_collections[0]

        old_scale = scene.unit_settings.scale_length

        # We set the scale of the scene for the export
        scene.unit_settings.scale_length = 0.01

        armatures = [
            obj for obj in collections[0].objects if obj.type == 'ARMATURE']

        object_action_pairs = []
        original_actions = []

        starting_frames = []
        ending_frames = []

        # For each armature, we make a copy of the current action
        for obj in armatures:

            curr_action = None
            copy_action = None

            if obj.animation_data and obj.animation_data.action:

                curr_action = obj.animation_data.action
                copy_action = curr_action.copy()

                curr_frame_range = curr_action.frame_range

                starting_frames.append(curr_frame_range[0])
                ending_frames.append(curr_frame_range[1])

            object_action_pairs.append((obj, copy_action))
            original_actions.append(curr_action)

        # We compute the starting and ending frames
        max_frame = min(starting_frames)
        min_frame = max(ending_frames)

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

        view_layer.active_layer_collection = old_active_layer_collection

        scene.unit_settings.scale_length = old_scale

        # We delete the baked action and set the original one back
        for i in range(0, len(object_action_pairs)):

            pair = object_action_pairs[i]
            action = original_actions[i]

            if action:

                pair[0].animation_data.action = action

            if pair[1]:

                pair[1].user_clear()
                bpy.data.actions.remove(pair[1])

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
