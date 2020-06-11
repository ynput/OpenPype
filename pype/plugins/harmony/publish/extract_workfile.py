import os
import shutil

import pype.api
from avalon import harmony


class ExtractWorkfile(pype.api.Extractor):
    """Extract the connected nodes to the composite instance."""

    label = "Extract Workfile"
    hosts = ["harmony"]
    families = ["workfile"]

    def process(self, instance):
        file_path = instance.context.data["currentFile"]
        staging_dir = self.staging_dir(instance)

        os.chdir(staging_dir)
        shutil.make_archive(
            instance.name,
            "zip",
            os.path.dirname(file_path)
        )
        zip_path = os.path.join(staging_dir, instance.name + ".zip")
        self.log.info(f"Output zip file: {zip_path}")

        representation = {
            "name": "tpl",
            "ext": "zip",
            "files": "{}.zip".format(instance.name),
            "stagingDir": staging_dir
        }
        instance.data["representations"] = [representation]
