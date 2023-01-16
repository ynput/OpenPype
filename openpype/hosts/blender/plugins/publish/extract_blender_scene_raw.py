import os

import bpy

from openpype.pipeline import publish


class ExtractBlenderSceneRaw(publish.Extractor):
    """Extract as Blender Scene (raw).

    This will preserve all references, construction history, etc.
    """

    label = "Blender Scene (Raw)"
    hosts = ["blender"]
    families = ["blenderScene", "layout"]
    scene_type = "blend"

    def process(self, instance):
        # Define extract output file path
        dir_path = self.staging_dir(instance)
        filename = "{0}.{1}".format(instance.name, self.scene_type)
        path = os.path.join(dir_path, filename)

        # We need to get all the data blocks for all the blender objects.
        # The following set will contain all the data blocks from version
        # 2.93 of Blender.
        data_blocks = set()

        for attr in dir(bpy.data):
            data_block = getattr(bpy.data, attr)
            if isinstance(data_block, bpy.types.bpy_prop_collection):
                data_blocks |= {*data_block}

        # Write the datablocks in a new blend file.
        bpy.data.libraries.write(path, data_blocks)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': self.scene_type,
            'ext': self.scene_type,
            'files': filename,
            "stagingDir": dir_path
        }
        instance.data["representations"].append(representation)

        self.log.info("Extracted instance '%s' to: %s" % (instance.name, path))
