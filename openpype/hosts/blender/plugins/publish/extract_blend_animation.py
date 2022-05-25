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

        for member in instance[:-1]:
            if isinstance(member, bpy.types.Collection):
                for obj in member.all_objects:
                    if obj and obj.type == "ARMATURE":
                        if obj.animation_data and obj.animation_data.action:
                            data_blocks.add(obj.animation_data.action)
                            data_blocks.add(obj)

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
