import os
from openpype.lib import PreLaunchHook
from openpype.hosts.flame.api import utils


class FlamePrelaunch(PreLaunchHook):
    """ Flame prelaunch hook

    Will make sure flame_script_dirs are coppied to user's folder defined
    in environment var FLAME_SCRIPT_DIR.
    """
    app_groups = ["flame"]

    def execute(self):
        # setting flame_script_dirs for scripts syncing
        flame_script_dirs = os.path.normpath(
            self.launch_context.env.get("FLAME_SCRIPT_DIR", None)
        )

        if flame_script_dirs:
            assert os.path.isdir(flame_script_dirs), (
                "Flame script dirs does not exists."
                f"FLAME_SCRIPT_DIR: `{flame_script_dirs}`"
            )
        self.log.debug(f"-- flame_script_dirs: `{flame_script_dirs}`")

        utils.setup(self.launch_context.env)
