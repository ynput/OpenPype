# -*- coding: utf-8 -*-
"""Extract work file."""
import os
import shutil
from zipfile import ZipFile

from openpype.pipeline import publish


class ExtractWorkfile(publish.Extractor):
    """Extract and zip complete workfile folder into zip."""

    label = "Extract Workfile"
    hosts = ["harmony"]
    families = ["workfile"]

    def process(self, instance):
        """Plugin entry point."""
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, "{}.tpl".format(instance.name))
        src = os.path.dirname(instance.context.data["currentFile"])
        self.log.info("Copying to {}".format(filepath))
        shutil.copytree(src, filepath)

        # Prep representation.
        os.chdir(staging_dir)
        shutil.make_archive(
            f"{instance.name}",
            "zip",
            os.path.join(staging_dir, f"{instance.name}.tpl")
        )
        # Check if archive is ok
        with ZipFile(os.path.basename(f"{instance.name}.zip")) as zr:
            if zr.testzip() is not None:
                raise Exception("File archive is corrupted.")

        representation = {
            "name": "tpl",
            "ext": "zip",
            "files": f"{instance.name}.zip",
            "stagingDir": staging_dir
        }
        instance.data["representations"] = [representation]
