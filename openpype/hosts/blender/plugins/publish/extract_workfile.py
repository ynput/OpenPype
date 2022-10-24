import os
import bpy

from openpype.pipeline import publish
from openpype.hosts.blender.api import get_compress_setting


class ExtractWorkfile(publish.Extractor):
    """Extract the scene as workfile blend file."""

    label = "Extract workfile"
    hosts = ["blender"]
    families = ["workfile"]
    
    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        bpy.ops.wm.save_as_mainfile(
            filepath=filepath,
            compress=get_compress_setting(),
            relative_remap=False,
            copy=True,
        )

        # Create representation dict
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