import os
from openpype.lib.applications import PreLaunchHook, LaunchTypes


class PreLaunchResolveLastWorkfile(PreLaunchHook):
    """Special hook to open last workfile for Resolve.

    Checks 'start_last_workfile', if set to False, it will not open last
    workfile. This property is set explicitly in Launcher.
    """
    order = 10
    app_groups = ["resolve"]
    launch_types = {LaunchTypes.local}

    def execute(self):
        if not self.data.get("start_last_workfile"):
            self.log.info("It is set to not start last workfile on start.")
            return

        last_workfile = self.data.get("last_workfile_path")
        if not last_workfile:
            self.log.warning("Last workfile was not collected.")
            return

        if not os.path.exists(last_workfile):
            self.log.info("Current context does not have any workfile yet.")
            return

        # Add path to launch environment for the startup script to pick up
        self.log.info(
            "Setting OPENPYPE_RESOLVE_OPEN_ON_LAUNCH to launch "
            f"last workfile: {last_workfile}"
        )
        key = "OPENPYPE_RESOLVE_OPEN_ON_LAUNCH"
        self.launch_context.env[key] = last_workfile
