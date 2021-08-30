from openpype.lib import PreLaunchHook
import os


class SetPath(PreLaunchHook):
    """Set current dir to workdir.

    Hook `GlobalHostDataHook` must be executed before this hook.
    """
    app_groups = ["houdini"]

    def execute(self):
        workdir = self.launch_context.env.get("AVALON_WORKDIR", "")
        if not workdir:
            self.log.warning("BUG: Workdir is not filled.")
            return

        os.chdir(workdir)
