import os
from pype.lib import PreLaunchHook


class NukeStudioLaunchArguments(PreLaunchHook):
    order = 0
    hosts = ["nukestudio"]

    def execute(self):
        """Prepare suprocess launch arguments for NukeX."""
        # Get executable
        executable = self.launch_context.launch_args[0]

        if isinstance(executable, str):
            executable = [executable]

        # Add `nukex` argument and make sure it's bind to execuable
        executable.append("--studio")

        self.launch_context.launch_args[0] = executable

        if self.data.get("start_last_workfile"):
            last_workfile = self.data.get("last_workfile_path")
            if os.path.exists(last_workfile):
                self.launch_context.launch_args.append(
                    "\"{}\"".format(last_workfile)
                )
