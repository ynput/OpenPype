import os
from openpype.lib import (
    PreLaunchHook,
    create_workdir_extra_folders
)


class AddLastWorkfileToLaunchArgs(PreLaunchHook):
    """Add last workfile path to launch arguments.

    This is not possible to do for all applications the same way.
    """

    # Execute after workfile template copy
    order = 15

    def execute(self):
        if not self.application.is_host:
            return

        env = self.data.get("env") or {}
        workdir = env.get("AVALON_WORKDIR")
        if not workdir or not os.path.exists(workdir):
            return

        host_name = self.application.host_name
        task_type = self.data["task_type"]
        task_name = self.data["task_name"]
        project_name = self.data["project_name"]

        create_workdir_extra_folders(
            workdir, host_name, task_type, task_name, project_name,
        )
