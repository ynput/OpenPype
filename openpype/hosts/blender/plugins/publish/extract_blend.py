import os

import bpy

# import avalon.blender.workio
import openpype.api


class ExtractBlend(openpype.api.Extractor):
    """Extract a blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout"]
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
