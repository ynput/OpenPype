import os
import json

import bpy
import bpy_extras
import bpy_extras.anim_utils

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


def get_all_parents(obj):
    """Get all recursive parents of object"""
    result = []
    while True:
        obj = obj.parent
        if not obj:
            break
        result.append(obj)
    return result


def get_highest_root(objects):
    # Get the highest object that is also in the collection
    included_objects = {obj.name_full for obj in objects}
    num_parents_to_obj = {}
    for obj in objects:
        if isinstance(obj, bpy.types.Object):
            parents = get_all_parents(obj)
            # included parents
            parents = [parent for parent in parents if
                       parent.name_full in included_objects]
            if not parents:
                # A node without parents must be a highest root
                return obj

            num_parents_to_obj.setdefault(len(parents), obj)

    minimum_parent = min(num_parents_to_obj)
    return num_parents_to_obj[minimum_parent]


class ExtractAnimationFBX(
        publish.Extractor,
        publish.OptionalPyblishPluginMixin,
):
    """Extract as animation."""

    label = "Extract FBX"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.debug("Performing extraction..")

        asset_group = instance.data["transientData"]["instance_node"]

        # Get objects in this collection (but not in children collections)
        # and for those objects include the children hierarchy
        # TODO: Would it make more sense for the Collect Instance collector
        #   to also always retrieve all the children?
        objects = set(asset_group.objects)

        # From the direct children of the collection find the 'root' node
        # that we want to export - it is the 'highest' node in a hierarchy
        root = get_highest_root(objects)

        for obj in list(objects):
            objects.update(obj.children_recursive)

        # Find all armatures among the objects, assume to find only one
        armatures = [obj for obj in objects if obj.type == "ARMATURE"]
        if not armatures:
            raise RuntimeError(
                f"Unable to find ARMATURE in collection: "
                f"{asset_group.name}"
            )
        elif len(armatures) > 1:
            self.log.warning(
                "Found more than one ARMATURE, using "
                f"only first of: {armatures}"
            )
        armature = armatures[0]

        object_action_pairs = []
        original_actions = []

        starting_frames = []
        ending_frames = []

        # For each armature, we make a copy of the current action
        if armature.animation_data and armature.animation_data.action:
            curr_action = armature.animation_data.action
            copy_action = curr_action.copy()

            curr_frame_range = curr_action.frame_range

            starting_frames.append(curr_frame_range[0])
            ending_frames.append(curr_frame_range[1])
        else:
            self.log.info(
                f"Armature '{armature.name}' has no animation, "
                f"skipping FBX animation extraction for {instance}."
            )
            return

        asset_group_name = asset_group.name
        asset_name = asset_group.get(AVALON_PROPERTY).get("asset_name")
        if asset_name:
            # Rename for the export; this data is only present when loaded
            # from a JSON Layout (layout family)
            asset_group.name = asset_name

        # Remove : from the armature name for the export
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

        root.select_set(True)
        armature.select_set(True)
        asset_name = instance.data["assetEntity"]["name"]
        subset = instance.data["subset"]
        instance_name = f"{asset_name}_{subset}"
        fbx_filename = f"{instance_name}_{armature.name}.fbx"
        filepath = os.path.join(stagingdir, fbx_filename)

        override = plugin.create_blender_context(
            active=root, selected=[root, armature])

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

        armature.name = armature_name
        asset_group.name = asset_group_name
        root.select_set(True)
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

        json_filename = f"{instance_name}.json"
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

        self.log.debug("Extracted instance '{}' to: {}".format(
                       instance.name, fbx_representation))
