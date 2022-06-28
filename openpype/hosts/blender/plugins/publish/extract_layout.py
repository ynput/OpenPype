import os
import json

from bson.objectid import ObjectId

import bpy
import bpy_extras
import bpy_extras.anim_utils

from openpype.pipeline import publish, legacy_io, AVALON_CONTAINER_ID
from openpype.client import get_representation_by_name
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractLayout(publish.Extractor):
    """Extract a layout as json."""

    label = "Extract Layout"
    hosts = ["blender"]
    families = ["layout"]
    optional = True

    def _export_animation(self, asset, instance, stagingdir, fbx_count):
        n = fbx_count

        for obj in asset.all_objects:
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
                self.log.info("Object have no animation.")
                continue

            armature_name = obj.name
            original_name = armature_name.split(':')[-1]
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

            obj.select_set(True)
            fbx_filename = f"{n:03d}.fbx"
            filepath = os.path.join(stagingdir, fbx_filename)

            bpy.ops.export_scene.fbx(
                plugin.create_blender_context(active=obj, selected=[obj]),
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
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        json_data = []
        fbx_files = []

        members = instance[:-1]

        fbx_count = 0

        assets = [
            member
            for member in members
            if (
                not member.override_library
                and member.get(AVALON_PROPERTY)
                and member.get(AVALON_PROPERTY).get("id") == (
                    AVALON_CONTAINER_ID
                )
            )
        ]

        project_name = instance.context.data["projectEntity"]["name"]
        for asset in assets:
            metadata = asset.get(AVALON_PROPERTY)

            # skip invalid assets
            for key in ("parent", "family", "asset_name", "libpath"):
                if key not in metadata:
                    self.log.debug(
                        f"Missing metadata for {asset.name}: {key}"
                    )
                    continue

            self.log.info(f"Extracting: {asset.name}")

            parent = metadata.get("parent")
            family = metadata.get("family")

            self.log.debug(f"Parent: {parent}")
            # Get blend reference
            blend = get_representation_by_name(
                project_name, "blend", parent, fields=["_id"]
            )
            blend_id = None
            if blend:
                blend_id = blend["_id"]
            # Get fbx reference
            fbx = get_representation_by_name(
                project_name, "fbx", parent, fields=["_id"]
            )
            fbx_id = None
            if fbx:
                fbx_id = fbx["_id"]
            # Get abc reference
            abc = get_representation_by_name(
                project_name, "abc", parent, fields=["_id"]
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
            json_element["namespace"] = metadata.get("namespace")
            json_element["asset_name"] = metadata.get("asset_name")
            json_element["file_path"] = metadata.get("libpath")

            if isinstance(asset, bpy.types.Object):
                json_element["transform"] = {
                    "translation": {
                        "x": asset.location.x,
                        "y": asset.location.y,
                        "z": asset.location.z
                    },
                    "rotation": {
                        "x": asset.rotation_euler.x,
                        "y": asset.rotation_euler.y,
                        "z": asset.rotation_euler.z,
                    },
                    "scale": {
                        "x": asset.scale.x,
                        "y": asset.scale.y,
                        "z": asset.scale.z
                    }
                }

            # Extract the animation as well
            if family == "rig":
                f, n = self._export_animation(
                    asset, instance, stagingdir, fbx_count
                )
                if f:
                    fbx_files.append(f)
                    json_element["animation"] = f
                    fbx_count = n

            json_data.append(json_element)

        json_filename = "{}.json".format(instance.name)
        json_path = os.path.join(stagingdir, json_filename)

        with open(json_path, "w+") as file:
            json.dump(json_data, fp=file, indent=2)

        instance.data.setdefault("representations", [])

        json_representation = {
            "name": "json",
            "ext": "json",
            "files": json_filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(json_representation)

        self.log.debug(fbx_files)

        fbx_representation = {
            "name": "fbx",
            "ext": "000.fbx" if len(fbx_files) == 1 else "fbx",
            "files": fbx_files[0] if len(fbx_files) == 1 else fbx_files,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(fbx_representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {json_representation}"
        )
