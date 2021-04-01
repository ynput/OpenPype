import os
from openpype.lib import PreLaunchHook


class LaunchWithWindowsShell(PreLaunchHook):
    """Add shell command before executable.

    Some hosts have issues when are launched directly from python in that case
    it is possible to prepend shell executable which will trigger process
    instead.
    """

    order = 10
    app_groups = ["resolve", "nuke", "nukex", "hiero", "nukestudio"]
    platforms = ["windows"]

    def execute(self):
        # Get comspec which is cmd.exe in most cases.
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        # Add comspec to arguments list and add "/k"
        new_args = [comspec, "/c"]
        new_args.extend(self.launch_context.launch_args)
        # Replace launch args with new one
        self.launch_context.launch_args = new_args
