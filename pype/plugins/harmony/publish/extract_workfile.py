# -*- coding: utf-8 -*-
"""Extract work file."""
import os
import shutil
from zipfile import ZipFile

from avalon import harmony

import pype.api
import pype.hosts.harmony


class ExtractWorkfile(pype.api.Extractor):
    """Extract the connected nodes to the composite instance."""

    label = "Extract Workfile"
    hosts = ["harmony"]
    families = ["workfile"]

    def process(self, instance):
        """Plugin entry point."""
        # Export template.
        backdrops = harmony.send(
            {"function": "Backdrop.backdrops", "args": ["Top"]}
        )["result"]
        nodes = instance.context.data.get("allNodes")
        staging_dir = self.staging_dir(instance)
        filepath = os.path.join(staging_dir, "{}.tpl".format(instance.name))

        pype.hosts.harmony.export_template(backdrops, nodes, filepath)

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
