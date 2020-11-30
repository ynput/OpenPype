import os
from pype.lib import PreLaunchHook


class MayaLaunchArguments(PreLaunchHook):
    """Add path to last workfile to launch arguments."""
    order = 0
    hosts = ["maya"]

    def execute(self):
        """Prepare suprocess launch arguments for Maya."""
        # Add path to workfile to arguments
        if self.data.get("start_last_workfile"):
            last_workfile = self.data.get("last_workfile_path")
            if os.path.exists(last_workfile):
                self.launch_context.launch_args.append(
                    "\"{}\"".format(last_workfile)
                )
