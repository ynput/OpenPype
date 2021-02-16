import os
from pype.lib import PreLaunchHook


class AddLastWorkfileToLaunchArgs(PreLaunchHook):
    """Add last workfile path to launch arguments.

    This is not possible to do for all applications the same way.
    """

    order = 0
    app_groups = ["maya", "nuke", "nukex", "hiero", "nukestudio"]

    def execute(self):
        if not self.data.get("start_last_workfile"):
            self.log.info("It is set to not start last workfile on start.")
            return

        last_workfile = self.data.get("last_workfile_path")
        if not last_workfile:
            self.log.warning("Last workfile was not collected.")
            return

        if not os.path.exists(last_workfile):
            self.log.info("Current context does not have any workfile yet.")
            return

        # Add path to workfile to arguments
        self.launch_context.launch_args.append(last_workfile)
