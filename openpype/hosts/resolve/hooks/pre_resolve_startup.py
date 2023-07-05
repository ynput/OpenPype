import os

from openpype.lib import PreLaunchHook
import openpype.hosts.resolve


class PreLaunchResolveStartup(PreLaunchHook):
    """Special hook to configure startup script.

    """
    order = 11
    app_groups = ["resolve"]

    def execute(self):
        # Set the openpype prelaunch startup script path for easy access
        # in the LUA .scriptlib code
        op_resolve_root = os.path.dirname(openpype.hosts.resolve.__file__)
        script_path = os.path.join(op_resolve_root, "startup.py")
        key = "OPENPYPE_RESOLVE_STARTUP_SCRIPT"
        self.launch_context.env[key] = script_path

        self.log.info(
            f"Setting OPENPYPE_RESOLVE_STARTUP_SCRIPT to: {script_path}"
        )
