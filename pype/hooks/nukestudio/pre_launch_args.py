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
