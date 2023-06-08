from concurrent.futures import Future, ThreadPoolExecutor
from functools import partial
import subprocess

import bpy
from bson.objectid import ObjectId
import pyblish

from openpype.hosts.blender.api.utils import BL_TYPE_DATAPATH
from openpype.hosts.blender.utility_scripts import (
    make_paths_relative,
    update_representations,
)
from openpype.modules.base import ModulesManager
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

        # Prepare pool for commands
        pool = ThreadPoolExecutor()

        # Get sites to sync with
        manager = ModulesManager()
        sync_server_module = manager.modules_by_name["sync_server"]
        site = sync_server_module.get_remote_site(project_name)

        # Get published and hero representations
        representations = instance.data.get("published_representations")
        representations.update(instance.data.get("hero_representations", {}))

        # Run commands for all published representations
        instance.data.setdefault("representations_futures", [])
        for representation in representations.values():
            representation = representation["representation"]
            published_path = representation.get("data", {}).get("path")

            # Set main command
            main_command = [bpy.app.binary_path, published_path, "-b"]

            # If not workfile, it is a blend and there is a published file
            if representation.get("name") == "blend" and published_path:
                repre_id = representation["_id"]

                # Pause representation on site
                sync_server_module.pause_representation(
                    project_name, repre_id, site
                )

                if use_path_management:
                    self.log.info(
                        f"Running {make_paths_relative.__file__}"
                        f"to {published_path}..."
                    )
                    # Make paths relative
                    main_command.extend(
                        [
                            "-P",
                            make_paths_relative.__file__,
                        ]
                    )

                self.log.info(
                    f"Running {update_representations.__file__}"
                    f"to {published_path}..."
                )
                main_command.extend(
                    [
                        "-P",
                        update_representations.__file__,
                        "--",
                        instance.data["subset"],
                        "--datablocks",
                        *[i.name for i in instance],
                        "--datapaths",
                        *{
                            BL_TYPE_DATAPATH.get(type(d))
                            for d in instance
                            if BL_TYPE_DATAPATH.get(type(d)) is not None
                        },
                        "--id",
                        str(repre_id),
                    ]
                )
                main_command.extend(
                    ["--published_time", instance.context.data["time"]]
                )

                # Build function to callback
                def callback(id: ObjectId, future: Future):
                    if future.exception() is not None:
                        raise future.exception()
                    else:
                        sync_server_module.unpause_representation(
                            project_name, id, site
                        )

                # Submit command to pool
                f = pool.submit(
                    subprocess.check_output,
                    main_command,
                    shell=False,
                    stderr=subprocess.PIPE,
                )
                f.add_done_callback(partial(callback, repre_id))

                # Keep future for waiting for it to finish at unpause
                instance.data["representations_futures"].append(f)
