import os
from openpype.lib import PreLaunchHook
from openpype.hosts.flame.api import utils
from pprint import pformat


class FlamePrelaunch(PreLaunchHook):
    """ Flame prelaunch hook

    Will make sure flame_script_dirs are coppied to user's folder defined
    in environment var FLAME_SCRIPT_DIR.
    """
    app_groups = ["flame"]

    def execute(self):
        self.log.info(pformat(dict(self.launch_context.env)))
        utils.setup(self.launch_context.env)
