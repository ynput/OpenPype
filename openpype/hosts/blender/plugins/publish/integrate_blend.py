from subprocess import Popen

import bpy

from openpype.hosts.blender.utility_scripts import make_paths_relative
from openpype.plugins.publish.integrate import IntegrateAsset
from openpype.settings.lib import get_project_settings


class IntegrateBlenderAsset(IntegrateAsset):
    label = "Integrate Blender Asset"
    hosts = ["blender"]

    def process(self, instance):
        # Check enabled in settings
        project_entity = instance.data["projectEntity"]
        project_name = project_entity["name"]
        project_settings = get_project_settings(project_name)
        host_name = instance.context.data["hostName"]
        host_settings = project_settings.get(host_name)
        if not host_settings:
            self.log.info('Host "{}" doesn\'t have settings'.format(host_name))
            return None

        if not host_settings.get("general", {}).get("use_paths_management"):
            return

        representations = instance.data.get("published_representations")

        for representation in representations.values():
            published_path = (
                representation.get("representation", {})
                .get("data", {})
                .get("path")
            )

            # If not workfile, it is a blend and there is a published file
            if (
                representation.get("representation", {}).get("name") == "blend"
                and published_path
            ):
                self.log.info(
                    f"Running {make_paths_relative.__file__}"
                    f"to {published_path}..."
                )
                # Run in subprocess
                subproc = Popen(
                    [
                        bpy.app.binary_path,
                        published_path,
                        "-b",
                        "-P",
                        make_paths_relative.__file__,
                    ]
                )
                subproc.wait()
