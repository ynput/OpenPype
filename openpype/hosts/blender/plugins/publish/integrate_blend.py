from subprocess import Popen

import bpy
import pyblish

from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH
from openpype.hosts.blender.utility_scripts import (
    make_paths_relative,
    update_representations,
)
from openpype.plugins.publish.integrate_hero_version import (
    IntegrateHeroVersion,
)
from openpype.settings.lib import get_project_settings


class IntegrateBlenderAsset(pyblish.api.InstancePlugin):
    label = "Integrate Blender Asset"
    hosts = ["blender"]
    order = IntegrateHeroVersion.order + 0.01

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

        use_path_management = host_settings.get("general", {}).get(
            "use_paths_management"
        )

        # Get published and hero representations
        representations = instance.data.get("published_representations")
        representations.update(instance.data.get("hero_representations", {}))

        for representation in representations.values():
            representation = representation["representation"]
            published_path = representation.get("data", {}).get("path")

            # Set main commands
            main_commands = [bpy.app.binary_path, published_path, "-b", "-P"]

            # If not workfile, it is a blend and there is a published file
            if representation.get("name") == "blend" and published_path:
                if use_path_management:
                    self.log.info(
                        f"Running {make_paths_relative.__file__}"
                        f"to {published_path}..."
                    )
                    # Run in subprocess
                    Popen(
                        [
                            *main_commands,
                            make_paths_relative.__file__,
                        ]
                    ).wait()

                self.log.info(
                    f"Running {update_representations.__file__}"
                    f"to {published_path}..."
                )
                # Run in subprocess
                Popen(
                    [
                        *main_commands,
                        update_representations.__file__,
                        "--",
                        instance.data["subset"],
                        "--datablocks",
                        *[i.name for i in instance],
                        "--datapaths",
                        *[BL_TYPE_DATAPATH.get(type(d)) for d in instance],
                        "--id",
                        str(representation["_id"]),
                    ]
                ).wait()
