from pathlib import Path
import avalon.blender.workio

import sonar.api


class ExtractModel(sonar.api.Extractor):
    """Extract as model."""

    label = "Model"
    hosts = ["blender"]
    families = ["model"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = Path(self.staging_dir(instance))
        filename = f"{instance.name}.blend"
        filepath = str(stagingdir / filename)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Just save the file to a temporary location. At least for now it's no
        # problem to have (possibly) extra stuff in the file.
        avalon.blender.workio.save_file(filepath, copy=True)

        # Store reference for integration
        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"].append(filename)

        self.log.info("Extracted instance '%s' to: %s", instance.name, filepath)
