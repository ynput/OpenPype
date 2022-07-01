import os

import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import plugin


class ExtractBlendAnimation(publish.Extractor):
    """Extract animation as blend file."""

    label = "Extract Anim Blend"
    hosts = ["blender"]
    families = ["animation"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        data_blocks = set()
        collections = set()
        animated_objects = set()

        for obj in instance:
            if plugin.is_container(obj, family="rig"):
                collections.add(obj)
            elif (
                isinstance(obj, bpy.types.Object)
                and obj.animation_data
                and obj.animation_data.action
            ):
                animated_objects.add(obj)

        for collection in collections:
            for obj in collection.all_objects:
                if obj.animation_data and obj.animation_data.action:
                    action = obj.animation_data.action.copy()
                    action_name = obj.animation_data.action.name.split(":")[-1]
                    action.name = f"{instance.name}:{action_name}"
                    action["collection"] = collection.name
                    action["armature"] = obj.name
                    data_blocks.add(action)

        for obj in animated_objects:
            action = obj.animation_data.action.copy()
            action_name = obj.animation_data.action.name.split(":")[-1]
            action.name = f"{instance.name}:{action_name}"
            action["collection"] = "NONE"
            action["armature"] = obj.name
            data_blocks.add(action)

        bpy.data.libraries.write(filepath, data_blocks)

        for action in data_blocks:
            bpy.data.actions.remove(action)

        representation = {
            "name": "blend",
            "ext": "blend",
            "files": filename,
            "stagingDir": stagingdir,
        }
        instance.data.setdefault("representations", [])
        instance.data["representations"].append(representation)

        self.log.info(
            f"Extracted instance '{instance.name}' to: {representation}"
        )
