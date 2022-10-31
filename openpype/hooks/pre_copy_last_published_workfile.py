import gc
import os
import shutil
from openpype.client.entities import (
    get_last_version_by_subset_id,
    get_representations,
    get_subsets,
)
from openpype.lib import PreLaunchHook
from openpype.modules.base import ModulesManager
from openpype.pipeline.load.utils import get_representation_path


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

        Returns:
            None: This is a void method.
        """
        # TODO setting
        self.log.info("Trying to fetch last published workfile...")

        last_workfile = self.data.get("last_workfile_path")
        if os.path.exists(last_workfile):
            self.log.debug(
                "Last workfile exists. Skipping {} process.".format(
                    self.__class__.__name__
                )
            )
            return

        project_name = self.data["project_name"]
        task_name = self.data["task_name"]

        project_doc = self.data.get("project_doc")
        asset_doc = self.data.get("asset_doc")
        anatomy = self.data.get("anatomy")
        if project_doc and asset_doc:
            # Get subset id
            subset_id = next(
                (
                    subset["_id"]
                    for subset in get_subsets(
                        project_name,
                        asset_ids=[asset_doc["_id"]],
                        fields=["_id", "data.family"],
                    )
                    if subset["data"]["family"] == "workfile"
                ),
                None,
            )
            if not subset_id:
                return

            # Get workfile representation
            workfile_representation = next(
                (
                    representation
                    for representation in get_representations(
                        project_name,
                        version_ids=[
                            get_last_version_by_subset_id(
                                project_name, subset_id, fields=["_id"]
                            )["_id"]
                        ],
                    )
                    if representation["context"]["task"]["name"] == task_name
                ),
                None,
            )

            if workfile_representation:  # TODO add setting
                # Get sync server from Tray, which handles the asynchronous thread instance
                sync_server = next(
                    (
                        t["sync_server"]
                        for t in [
                            obj
                            for obj in gc.get_objects()
                            if isinstance(obj, ModulesManager)
                        ]
                        if t["sync_server"].sync_server_thread
                    ),
                    None,
                )

                # Add site and reset timer
                active_site = sync_server.get_active_site(project_name)
                sync_server.add_site(
                    project_name,
                    workfile_representation["_id"],
                    active_site,
                    force=True,
                )
                sync_server.reset_timer()

                # Wait for the download loop to end
                sync_server.sync_server_thread.files_processed.wait()

                # Get paths
                published_workfile_path = get_representation_path(
                    workfile_representation, root=anatomy.roots
                )
                local_workfile_dir = os.path.dirname(last_workfile)

                # Copy file and substitute path
                self.data["last_workfile_path"] = shutil.copy(
                    published_workfile_path, local_workfile_dir
                )
