import os
from openpype.client.entities import (
    get_last_version_by_subset_id,
    match_subset_id,
    get_representation_by_task,
)

from openpype.lib import PreLaunchHook
from openpype.lib.profiles_filtering import filter_profiles
from openpype.settings.lib import get_project_settings
from openpype.modules.sync_server.sync_server import (
    get_last_published_workfile_path,
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

        self.log.info("Trying to fetch last published workfile...")

        asset_doc = self.data.get("asset_doc")
        anatomy = self.data.get("anatomy")

        # Get subset ID
        subset_id = match_subset_id(
            project_name, task_name, "workfile", asset_doc
        )
        if subset_id is None:
            self.log.debug(
                "Not any matched subset for task '{}' of '{}'.".format(
                    task_name, asset_name
                )
            )
            return

        # Get workfile representation
        last_version_doc = get_last_version_by_subset_id(
            project_name, subset_id, fields=["_id", "name"]
        )
        if not last_version_doc:
            self.log.debug("Subset does not have any versions")
            return

        workfile_representation = get_representation_by_task(
            project_name,
            task_name,
            last_version_doc,
        )
        if not workfile_representation:
            self.log.debug(
                'No published workfile for task "{}" and host "{}".'.format(
                    task_name, host_name
                )
            )
            return

        # Get last published
        published_workfile_path = get_last_published_workfile_path(
            host_name,
            project_name,
            task_name,
            workfile_representation,
            anatomy=anatomy,
        )

        # Copy file and substitute path
        self.data["last_workfile_path"] = download_last_published_workfile(
            host_name,
            project_name,
            asset_name,
            task_name,
            published_workfile_path,
            workfile_representation,
            subset_id,
            last_version_doc,
            anatomy=anatomy,
            asset_doc=asset_doc,
        )
        # Keep source filepath for further path conformation
        self.data["source_filepath"] = published_workfile_path
