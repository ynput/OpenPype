import os
import shutil
from time import sleep
from openpype.client.entities import (
    get_last_version_by_subset_id,
    get_representation_by_id,
    get_representation_last_created_time_on_site,
    get_representations,
    get_subsets,
)
from openpype.lib import PreLaunchHook
from openpype.lib.local_settings import get_local_site_id
from openpype.lib.profiles_filtering import filter_profiles
from openpype.pipeline.load.utils import get_representation_path
from openpype.settings.lib import get_project_settings


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
                    ' Can\'t access custom templates in host "{}".'
                ).format(host_name)
            )
            return
        elif use_last_published_workfile is False:
            self.log.info(
                (
                    'Project "{}" has turned off to use last published'
                    ' workfile as first workfile for host "{}"'
                ).format(project_name, host_name)
            )
            return

        self.log.info("Trying to fetch last published workfile...")

        project_doc = self.data.get("project_doc")
        asset_doc = self.data.get("asset_doc")
        anatomy = self.data.get("anatomy")

        # Check it can proceed
        if not project_doc and not asset_doc:
            return

        # Get subset id
        subset_id = next(
            (
                subset["_id"]
                for subset in get_subsets(
                    project_name,
                    asset_ids=[asset_doc["_id"]],
                    fields=["_id", "data.family", "data.families"],
                )
                if subset["data"].get("family") == "workfile"
                # Legacy compatibility
                or "workfile" in subset["data"].get("families", {})
            ),
            None,
        )
        if not subset_id:
            self.log.debug('No any workfile for asset "{}".').format(
                asset_doc["name"]
            )
            return

        # Get workfile representation
        last_version_doc = get_last_version_by_subset_id(
            project_name, subset_id, fields=["_id"]
        )
        if not last_version_doc:
            self.log.debug("Subset does not have any versions")
            return

        workfile_representation = next(
            (
                representation
                for representation in get_representations(
                    project_name,
                    version_ids=[last_version_doc["_id"]]
                )
                if representation["context"]["task"]["name"] == task_name
            ),
            None,
        )

        if not workfile_representation:
            self.log.debug(
                'No published workfile for task "{}" and host "{}".'
            ).format(task_name, host_name)
            return

        local_site_id = get_local_site_id()
        sync_server = self.modules_manager.get("sync_server")
        sync_server.add_site(
            project_name,
            workfile_representation["_id"],
            local_site_id,
            force=True,
            priority=99,
            reset_timer=True
        )

        while not sync_server.is_representaion_on_site(
            project_name,
            workfile_representation["_id"],
            local_site_id
        ):
            sleep(5)

        # Get paths
        published_workfile_path = get_representation_path(
            workfile_representation, root=anatomy.roots
        )
        local_workfile_dir = os.path.dirname(last_workfile)

        # Copy file and substitute path
        self.data["last_workfile_path"] = shutil.copy(
            published_workfile_path, local_workfile_dir
        )
