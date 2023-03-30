import os
from openpype.client.entities import (
    get_representations,
)

from openpype.lib import PreLaunchHook
from openpype.lib.profiles_filtering import filter_profiles
from openpype.pipeline.load.utils import get_representation_path_with_anatomy
from openpype.settings.lib import get_project_settings
from openpype.modules.sync_server.sync_server import (
    download_last_published_workfile,
)


class CopyLastPublishedWorkfile(PreLaunchHook):
    """Copy last published workfile as first workfile.

    Prelaunch hook works only if last workfile leads to not existing file.
        - That is possible only if it's first version.
    """

    # Before `AddLastWorkfileToLaunchArgs`
    order = -1
    app_groups = ["blender", "photoshop", "tvpaint", "aftereffects"]

    def execute(self):
        """Check if local workfile doesn't exist, else copy it.

        1- Check if setting for this feature is enabled
        2- Check if workfile in work area doesn't exist
        3- Check if published workfile exists and is copied locally in publish
        4- Substitute copied published workfile as first workfile
           with incremented version by +1

        Returns:
            None: This is a void method.
        """
        sync_server = self.modules_manager.get("sync_server")
        if not sync_server or not sync_server.enabled:
            self.log.debug("Sync server module is not enabled or available")
            return

        # Check there is no workfile available
        last_workfile = self.data.get("last_workfile_path")
        if os.path.exists(last_workfile):
            self.log.debug(
                "Last workfile exists. Skipping {} process.".format(
                    self.__class__.__name__
                )
            )
            return

        # Get data
        project_name = self.data["project_name"]
        asset_name = self.data["asset_name"]
        task_name = self.data["task_name"]
        task_type = self.data["task_type"]
        host_name = self.application.host_name

        # Check settings has enabled it
        project_settings = get_project_settings(project_name)
        profiles = project_settings["global"]["tools"]["Workfiles"][
            "last_workfile_on_startup"
        ]
        filter_data = {
            "tasks": task_name,
            "task_types": task_type,
            "hosts": host_name,
        }
        last_workfile_settings = filter_profiles(profiles, filter_data)
        use_last_published_workfile = last_workfile_settings.get(
            "use_last_published_workfile"
        )
        if use_last_published_workfile is None:
            self.log.info(
                (
                    "Seems like old version of settings is used."
                    ' Can\'t access custom templates in host "{}".'.format(
                        host_name
                    )
                )
            )
            return
        elif use_last_published_workfile is False:
            self.log.info(
                (
                    'Project "{}" has turned off to use last published'
                    ' workfile as first workfile for host "{}"'.format(
                        project_name, host_name
                    )
                )
            )
            return

        max_retries = int((sync_server.sync_project_settings[project_name]
                                                            ["config"]
                                                            ["retry_cnt"]))

        self.log.info("Trying to fetch last published workfile...")

        asset_doc = self.data.get("asset_doc")
        anatomy = self.data.get("anatomy")

        context_filters = {
            "asset": asset_name,
            "family": "workfile",
            "task": {"name": task_name, "type": task_type}
        }

        workfile_representations = list(get_representations(
            project_name,
            context_filters=context_filters
        ))

        if not workfile_representations:
            self.log.debug(
                'No published workfile for task "{}" and host "{}".'.format(
                    task_name, host_name
                )
            )
            return

        sorted_workfile_representations = sorted(workfile_representations,
                                                 key=lambda d: d["context"]
                                                                ["version"])

        workfile_representation = sorted_workfile_representations[-1]
        # Get last published
        published_workfile_path = get_representation_path_with_anatomy(
            workfile_representation, anatomy
        )

        # Copy file and substitute path
        self.data["last_workfile_path"] = download_last_published_workfile(
            host_name,
            project_name,
            asset_name,
            task_name,
            published_workfile_path,
            workfile_representation,
            max_retries,
            anatomy=anatomy,
            asset_doc=asset_doc,
        )
        # Keep source filepath for further path conformation
        self.data["source_filepath"] = published_workfile_path
