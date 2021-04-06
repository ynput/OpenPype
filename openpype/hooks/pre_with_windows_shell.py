import os
import subprocess
from openpype.lib import PreLaunchHook


class LaunchWithWindowsShell(PreLaunchHook):
    """Add shell command before executable.

    Some hosts have issues when are launched directly from python in that case
    it is possible to prepend shell executable which will trigger process
    instead.
    """

    # Should be as last hook becuase must change launch arguments to string
    order = 1000
    app_groups = ["resolve", "nuke", "nukex", "hiero", "nukestudio"]
    platforms = ["windows"]

    def execute(self):
        new_args = [
            # Get comspec which is cmd.exe in most cases.
            os.environ.get("COMSPEC", "cmd.exe"),
            # NOTE change to "/k" if want to keep console opened
            "/c",
            # Convert arguments to command line arguments (as string)
            "\"{}\"".format(
                subprocess.list2cmdline(self.launch_context.launch_args)
            )
        ]
        # Convert list to string
        # WARNING this only works if is used as string
        args_string = " ".join(new_args)
        self.log.info((
            "Modified launch arguments to be launched with shell \"{}\"."
        ).format(args_string))

        # Replace launch args with new one
        self.launch_context.launch_args = args_string
        # Change `creationflags` to CREATE_NEW_CONSOLE
        self.launch_context.kwargs["creationflags"] = (
            subprocess.CREATE_NEW_CONSOLE
        )
