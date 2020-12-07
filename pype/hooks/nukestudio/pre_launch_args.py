import os
from pype.lib import PreLaunchHook


class NukeStudioLaunchArguments(PreLaunchHook):
    order = 0
    app_groups = ["nukestudio"]

    def execute(self):
        """Prepare suprocess launch arguments for NukeStudio."""
        # Add path to workfile to arguments
        if self.data.get("start_last_workfile"):
            last_workfile = self.data.get("last_workfile_path")
            if os.path.exists(last_workfile):
                self.launch_context.launch_args.append(last_workfile)
