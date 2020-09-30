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

        context = bpy.context
        scene = context.scene

        # Perform extraction
        self.log.info("Performing extraction..")

        collections = [
            obj for obj in instance if type(obj) is bpy.types.Collection]

        assert len(collections) == 1, "There should be one and only one " \
            "collection collected for this asset"

        old_scale = scene.unit_settings.scale_length

        # We set the scale of the scene for the export
        scene.unit_settings.scale_length = 0.01

        armatures = [
            obj for obj in collections[0].objects if obj.type == 'ARMATURE']

        assert len(collections) == 1, "There should be one and only one " \
            "armature collected for this asset"

        armature = armatures[0]

        armature_name = armature.name
        original_name = armature_name.split(':')[0]
        armature.name = original_name

        object_action_pairs = []
        original_actions = []

        starting_frames = []
        ending_frames = []

        # For each armature, we make a copy of the current action
        curr_action = None
        copy_action = None

        if armature.animation_data and armature.animation_data.action:
            curr_action = armature.animation_data.action
            copy_action = curr_action.copy()

            curr_frame_range = curr_action.frame_range

            starting_frames.append(curr_frame_range[0])
            ending_frames.append(curr_frame_range[1])
        else:
            self.log.info("Object have no animation.")
            return

        object_action_pairs.append((armature, copy_action))
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

        for obj in bpy.data.objects:
            obj.select_set(False)

        armature.select_set(True)
        fbx_filename = f"{instance.name}_{armature.name}.fbx"
        filepath = os.path.join(stagingdir, fbx_filename)

        override = bpy.context.copy()
        override['selected_objects'] = [armature]
        bpy.ops.export_scene.fbx(
            override,
            filepath=filepath,
            use_selection=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            add_leaf_bones=False,
            armature_nodetype='ROOT',
            object_types={'ARMATURE'}
        )
        armature.name = armature_name
        armature.select_set(False)

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

        fbx_representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': fbx_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(fbx_representation)

        self.log.info("Extracted instance '{}' to: {}".format(
                      instance.name, fbx_representation))
