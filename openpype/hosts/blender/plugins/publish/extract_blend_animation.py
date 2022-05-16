import os

import bpy

import openpype.api
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class ExtractBlendAnimation(openpype.api.Extractor):
    """Extract a blend file."""

    label = "Extract Blend"
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

        for obj in instance:
            if (
                isinstance(obj, bpy.types.Object) and
                obj.type == 'ARMATURE' and
                obj.animation_data and
                obj.animation_data.action
            ):
                action = obj.animation_data.action
                data_blocks.add(action)

                if not action.get(AVALON_PROPERTY):
                    action[AVALON_PROPERTY] = {
                        "namespaces": set(),
                        "users": set(),
                        "family": "action",
                        "objectName": action.name,
                    }

                action[AVALON_PROPERTY]["users"].add(obj.name)

                for collection in obj.users_collection:
                    metadata = collection.get(AVALON_PROPERTY)
                    if metadata and metadata.get("namespace"):
                        action[AVALON_PROPERTY]["namespaces"].add(
                            metadata.get("namespace")
                        )

        bpy.data.libraries.write(filepath, data_blocks)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': 'blend',
            'ext': 'blend',
            'files': filename,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s",
                      instance.name, representation)
