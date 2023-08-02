import subprocess
from openpype.lib.applications import PreLaunchHook, LaunchTypes


class BlenderConsoleWindows(PreLaunchHook):
    """Foundry applications have specific way how to launch them.

    Blender is executed "like" python process so it is required to pass
    `CREATE_NEW_CONSOLE` flag on windows to trigger creation of new console.
    At the same time the newly created console won't create it's own stdout
    and stderr handlers so they should not be redirected to DEVNULL.
    """

    # Should be as last hook because must change launch arguments to string
    order = 1000
    app_groups = ["blender"]
    platforms = ["windows"]
    launch_types = {LaunchTypes.local}

    def execute(self):
        # Change `creationflags` to CREATE_NEW_CONSOLE
        # - on Windows will blender create new window using it's console
        # Set `stdout` and `stderr` to None so new created console does not
        #   have redirected output to DEVNULL in build
        self.launch_context.kwargs.update({
            "creationflags": subprocess.CREATE_NEW_CONSOLE,
            "stdout": None,
            "stderr": None
        })
