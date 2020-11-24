import os
from pype.lib import PreLaunchHook


class HieroLaunchArguments(PreLaunchHook):
    order = 0
    hosts = ["hiero"]

    def execute(self):
        """Prepare suprocess launch arguments for NukeX."""
        # Get executable
        executable = self.launch_context.launch_args[0]

        if isinstance(executable, str):
            executable = [executable]

        # Add `nukex` argument and make sure it's bind to execuable
        executable.append("--hiero")

        self.launch_context.launch_args[0] = executable

        if self.data.get("start_last_workfile"):
            last_workfile = self.data.get("last_workfile_path")
            if os.path.exists(last_workfile):
                self.launch_context.launch_args.append(
                    "\"{}\"".format(last_workfile)
                )
