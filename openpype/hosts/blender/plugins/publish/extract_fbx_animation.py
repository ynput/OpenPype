import os
import json

import bpy
import bpy_extras
import bpy_extras.anim_utils

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractAnimationFBX(publish.Extractor):
    """Extract animation as FBX."""

    label = "Extract Anim FBX"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def _export_animation(self, armature, stagingdir, fbx_count):

        object_action_pairs = []
        original_actions = []

        starting_frames = []
        ending_frames = []

        # For each armature, we make a copy of the current action
        curr_action = armature.animation_data.action
        copy_action = curr_action.copy()

        curr_frame_range = curr_action.frame_range

        starting_frames.append(curr_frame_range[0])
        ending_frames.append(curr_frame_range[1])

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

        plugin.deselect_all()

        armature.select_set(True)
        fbx_filename = f"{fbx_count:03d}.fbx"
        filepath = os.path.join(stagingdir, fbx_filename)

        with plugin.context_override(active=armature, selected=armature):
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_active_collection=False,
                use_selection=True,
                bake_anim_use_nla_strips=False,
                bake_anim_use_all_actions=False,
                add_leaf_bones=False,
                armature_nodetype="ROOT",
                object_types={"EMPTY", "ARMATURE"}
            )
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

        return fbx_filename

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        collections = [
            obj
            for obj in set(instance[:-1])
            if plugin.is_container(obj, family="rig")
        ]

        json_data = []
        fbx_files = []

        for collection in collections:
            metadata = collection.get(AVALON_PROPERTY)
            armatures = [
                obj
                for obj in collection.all_objects
                if obj.type == "ARMATURE"
            ]
            for armature in armatures:
                if armature.animation_data and armature.animation_data.action:
                    fbx_filename = self._export_animation(
                        armature, stagingdir, len(fbx_files)
                    )
                    json_data.append({
                        "instance_name": instance.name,
                        "namespace": metadata.get("namespace"),
                        "asset_name": metadata.get("asset_name"),
                        "family": metadata.get("family"),
                        "libpath": metadata.get("libpath"),
                        "objectName": collection.name,
                        "armatureName": armature.name,
                        "fbx_filename": fbx_filename,
                    })
                    fbx_files.append(fbx_filename)
                else:
                    self.log.info(f"No animation for: {armature.name}")

        json_filename = f"{instance.name}.json"
        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as f:
            json.dump(json_data, fp=f, indent=2)

        instance.data.setdefault("representations", [])

        fbx_representation = {
            "name": "fbx",
            "ext": "000.fbx" if len(fbx_files) == 1 else "fbx",
            "files": fbx_files[0] if len(fbx_files) == 1 else fbx_files,
            "stagingDir": stagingdir,
        }
        json_representation = {
            "name": "json",
            "ext": "json",
            "files": json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(fbx_representation)
        instance.data["representations"].append(json_representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: '{fbx_representation}'"
        )
