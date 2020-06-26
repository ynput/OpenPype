import os
import avalon.blender.workio

import pype.api


class ExtractBlend(pype.api.Extractor):
    """Extract a blend file."""

    label = "Extract Blend"
    hosts = ["blender"]
    families = ["model", "camera", "rig", "action", "layout", "animation"]
    optional = True

    def process(self, instance):
        # Define extract output file path

        stagingdir = self.staging_dir(instance)
        filename = f"{instance.name}.blend"
        filepath = os.path.join(stagingdir, filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Just save the file to a temporary location. At least for now it's no
        # problem to have (possibly) extra stuff in the file.
        avalon.blender.workio.save_file(filepath, copy=True)
        #
        # # Store reference for integration
        # if "files" not in instance.data:
        #     instance.data["files"] = list()
        #
        # # instance.data["files"].append(filename)

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
