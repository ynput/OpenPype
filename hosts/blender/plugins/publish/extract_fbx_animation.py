import os
import json

import bpy
import bpy_extras
import bpy_extras.anim_utils

from openpype import api
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractAnimationFBX(api.Extractor):
    """Extract as animation."""

    label = "Extract FBX"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        # The first collection object in the instance is taken, as there
        # should be only one that contains the asset group.
        collection = [
            obj for obj in instance if type(obj) is bpy.types.Collection][0]

        # Again, the first object in the collection is taken , as there
        # should be only the asset group in the collection.
        asset_group = collection.objects[0]

        armature = [
            obj for obj in asset_group.children if obj.type == 'ARMATURE'][0]

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

        asset_group_name = asset_group.name
        asset_group.name = asset_group.get(AVALON_PROPERTY).get("asset_name")

        armature_name = armature.name
        original_name = armature_name.split(':')[1]
        armature.name = original_name

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

        asset_group.select_set(True)
        armature.select_set(True)
        fbx_filename = f"{instance.name}_{armature.name}.fbx"
        filepath = os.path.join(stagingdir, fbx_filename)

        override = plugin.create_blender_context(
            active=asset_group, selected=[asset_group, armature])
        bpy.ops.export_scene.fbx(
            override,
            filepath=filepath,
            use_active_collection=False,
            use_selection=True,
            bake_anim_use_nla_strips=False,
            bake_anim_use_all_actions=False,
            add_leaf_bones=False,
            armature_nodetype='ROOT',
            object_types={'EMPTY', 'ARMATURE'}
        )
        armature.name = armature_name
        asset_group.name = asset_group_name
        asset_group.select_set(False)
        armature.select_set(False)

        # We delete the baked action and set the original one back
        for i in range(0, len(object_action_pairs)):
            pair = object_action_pairs[i]
            action = original_actions[i]

            if action:
                pair[0].animation_data.action = action

            if pair[1]:
                pair[1].user_clear()
                bpy.data.actions.remove(pair[1])

        json_filename = f"{instance.name}.json"
        json_path = os.path.join(stagingdir, json_filename)

        json_dict = {
            "instance_name": asset_group.get(AVALON_PROPERTY).get("objectName")
        }

        # collection = instance.data.get("name")
        # container = None
        # for obj in bpy.data.collections[collection].objects:
        #     if obj.type == "ARMATURE":
        #         container_name = obj.get("avalon").get("container_name")
        #         container = bpy.data.collections[container_name]
        # if container:
        #     json_dict = {
        #         "instance_name": container.get("avalon").get("instance_name")
        #     }

        with open(json_path, "w+") as file:
            json.dump(json_dict, fp=file, indent=2)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        fbx_representation = {
            'name': 'fbx',
            'ext': 'fbx',
            'files': fbx_filename,
            "stagingDir": stagingdir,
        }
        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(fbx_representation)
        instance.data["representations"].append(json_representation)

        self.log.info("Extracted instance '{}' to: {}".format(
                      instance.name, fbx_representation))
