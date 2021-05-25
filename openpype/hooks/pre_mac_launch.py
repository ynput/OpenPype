from openpype.lib import PreLaunchHook


class LaunchWithTerminal(PreLaunchHook):
    """Mac specific pre arguments for application.

    Mac applications should be launched using "open" argument which is internal
    callbacks to open executable. We also add argument "-an" to create new
    process. This is used only for executables ending with ".app". It is
    expected that these executables lead to app packages.
    """
    order = 1000

    platforms = ["darwin"]

    def execute(self):
        if self.launch_context.executable.endswith(".app"):
            self.launch_context.launch_args.insert(0, ["open", "-an"])
