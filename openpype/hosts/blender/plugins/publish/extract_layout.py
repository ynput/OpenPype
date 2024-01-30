import os
import json

import bpy
import bpy_extras
import bpy_extras.anim_utils

from openpype.client import get_representation_by_name
from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractLayout(publish.Extractor, publish.OptionalPyblishPluginMixin):
    """Extract a layout."""

    label = "Extract Layout (JSON)"
    hosts = ["blender"]
    families = ["layout"]
    optional = True

    def _export_animation(self, asset, instance, stagingdir, fbx_count):
        n = fbx_count

        for obj in asset.children:
            if obj.type != "ARMATURE":
                continue

            object_action_pairs = []
            original_actions = []

            starting_frames = []
            ending_frames = []

            # For each armature, we make a copy of the current action
            curr_action = None
            copy_action = None

            if obj.animation_data and obj.animation_data.action:
                curr_action = obj.animation_data.action
                copy_action = curr_action.copy()

                curr_frame_range = curr_action.frame_range

                starting_frames.append(curr_frame_range[0])
                ending_frames.append(curr_frame_range[1])
            else:
                self.log.info("Object has no animation.")
                continue

            asset_group_name = asset.name
            asset.name = asset.get(AVALON_PROPERTY).get("asset_name")

            armature_name = obj.name
            original_name = armature_name.split(':')[1]
            obj.name = original_name

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

            for o in bpy.data.objects:
                o.select_set(False)

            asset.select_set(True)
            obj.select_set(True)
            fbx_filename = f"{n:03d}.fbx"
            filepath = os.path.join(stagingdir, fbx_filename)

            override = plugin.create_blender_context(
                active=asset, selected=[asset, obj])
            with bpy.context.temp_override(**override):
                # We export the fbx
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_active_collection=False,
                    use_selection=True,
                    bake_anim_use_nla_strips=False,
                    bake_anim_use_all_actions=False,
                    add_leaf_bones=False,
                    armature_nodetype='ROOT',
                    object_types={'EMPTY', 'ARMATURE'}
                )
            obj.name = armature_name
            asset.name = asset_group_name
            asset.select_set(False)
            obj.select_set(False)

            # We delete the baked action and set the original one back
            for i in range(0, len(object_action_pairs)):
                pair = object_action_pairs[i]
                action = original_actions[i]

                if action:
                    pair[0].animation_data.action = action

                if pair[1]:
                    pair[1].user_clear()
                    bpy.data.actions.remove(pair[1])

            return fbx_filename, n + 1

        return None, n

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.debug("Performing extraction..")

        if "representations" not in instance.data:
            instance.data["representations"] = []

        json_data = []
        fbx_files = []

        asset_group = instance.data["transientData"]["instance_node"]

        fbx_count = 0

        project_name = instance.context.data["projectEntity"]["name"]
        for asset in asset_group.children:
            metadata = asset.get(AVALON_PROPERTY)
            if not metadata:
                # Avoid raising error directly if there's just invalid data
                # inside the instance; better to log it to the artist
                # TODO: This should actually be validated in a validator
                self.log.warning(
                    f"Found content in layout that is not a loaded "
                    f"asset, skipping: {asset.name_full}"
                )
                continue

            version_id = metadata["parent"]
            family = metadata["family"]

            self.log.debug("Parent: {}".format(version_id))
            # Get blend reference
            blend = get_representation_by_name(
                project_name, "blend", version_id, fields=["_id"]
            )
            blend_id = None
            if blend:
                blend_id = blend["_id"]
            # Get fbx reference
            fbx = get_representation_by_name(
                project_name, "fbx", version_id, fields=["_id"]
            )
            fbx_id = None
            if fbx:
                fbx_id = fbx["_id"]
            # Get abc reference
            abc = get_representation_by_name(
                project_name, "abc", version_id, fields=["_id"]
            )
            abc_id = None
            if abc:
                abc_id = abc["_id"]

            json_element = {}
            if blend_id:
                json_element["reference"] = str(blend_id)
            if fbx_id:
                json_element["reference_fbx"] = str(fbx_id)
            if abc_id:
                json_element["reference_abc"] = str(abc_id)
            json_element["family"] = family
            json_element["instance_name"] = asset.name
            json_element["asset_name"] = metadata["asset_name"]
            json_element["file_path"] = metadata["libpath"]

            json_element["transform"] = {
                "translation": {
                    "x": asset.location.x,
                    "y": asset.location.y,
                    "z": asset.location.z
                },
                "rotation": {
                    "x": asset.rotation_euler.x,
                    "y": asset.rotation_euler.y,
                    "z": asset.rotation_euler.z
                },
                "scale": {
                    "x": asset.scale.x,
                    "y": asset.scale.y,
                    "z": asset.scale.z
                }
            }

            json_element["transform_matrix"] = []

            for row in list(asset.matrix_world.transposed()):
                json_element["transform_matrix"].append(list(row))

            json_element["basis"] = [
                [1, 0, 0, 0],
                [0, -1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ]

            # Extract the animation as well
            if family == "rig":
                f, n = self._export_animation(
                    asset, instance, stagingdir, fbx_count)
                if f:
                    fbx_files.append(f)
                    json_element["animation"] = f
                    fbx_count = n

            json_data.append(json_element)

        asset_name = instance.data["assetEntity"]["name"]
        subset = instance.data["subset"]
        instance_name = f"{asset_name}_{subset}"
        json_filename = f"{instance_name}.json"

        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        json_representation = {
            'name': 'json',
            'ext': 'json',
            'files': json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(json_representation)

        self.log.debug(fbx_files)

        if len(fbx_files) == 1:
            fbx_representation = {
                'name': 'fbx',
                'ext': '000.fbx',
                'files': fbx_files[0],
                "stagingDir": stagingdir,
            }
            instance.data["representations"].append(fbx_representation)
        elif len(fbx_files) > 1:
            fbx_representation = {
                'name': 'fbx',
                'ext': 'fbx',
                'files': fbx_files,
                "stagingDir": stagingdir,
            }
            instance.data["representations"].append(fbx_representation)

        self.log.debug("Extracted instance '%s' to: %s",
                       instance.name, json_representation)
