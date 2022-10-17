from subprocess import Popen

import bpy

from openpype.hosts.blender.utility_scripts import make_paths_relative
from openpype.plugins.publish.integrate import IntegrateAsset


class IntegrateBlenderAsset(IntegrateAsset):
    label = "Integrate Blender Asset"
    hosts = ["blender"]

    def process(self, instance):
        representations = instance.data.get("published_representations")

        for repre_id, representation in representations.items():
            published_path = (
                representation.get("representation", {})
                .get("data", {})
                .get("path")
            )

            # If not workfile, it is a blend and there is a published file
            if (
                representation.get("anatomy_data", {}).get("family")
                != "workfile"
                and representation.get("representation", {}).get("name")
                == "blend"
                and published_path
            ):
                self.log.info(
                    f"Running {make_paths_relative.__file__} to {published_path}..."
                )
                # Run in subprocess
                Popen(
                    [
                        bpy.app.binary_path,
                        published_path,
                        "-b",
                        "-P",
                        make_paths_relative.__file__,
                    ]
                )
