import os

import bpy

import openpype.api


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
            if isinstance(obj, bpy.types.Object) and obj.type == 'EMPTY':
                child = obj.children[0]
                if child and child.type == 'ARMATURE':
                    if child.animation_data and child.animation_data.action:
                        if not obj.animation_data:
                            obj.animation_data_create()
                        obj.animation_data.action = child.animation_data.action
                        obj.animation_data_clear()
                        data_blocks.add(child.animation_data.action)
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
