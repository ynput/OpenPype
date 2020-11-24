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
