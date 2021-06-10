import subprocess
from openpype.lib import PreLaunchHook


class LaunchWindowsShell(PreLaunchHook):
    """Add shell command before executable.

    Some hosts have issues when are launched directly from python in that case
    it is possible to prepend shell executable which will trigger process
    instead.
    """

    # Should be as last hook because must change launch arguments to string
    order = 1000
    app_groups = ["nuke", "nukex", "hiero", "nukestudio"]
    platforms = ["windows"]

    def execute(self):
        # Change `creationflags` to CREATE_NEW_CONSOLE
        # - on Windows will nuke create new window using it's console
        # Set `stdout` and `stderr` to None so new created console does not
        #   have redirected output to DEVNULL in build
        self.launch_context.kwargs.update({
            "creationflags": subprocess.CREATE_NEW_CONSOLE,
            "stdout": None,
            "stderr": None
        })
