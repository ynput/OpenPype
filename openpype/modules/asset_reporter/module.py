import os.path

from openpype import AYON_SERVER_ENABLED
from openpype.modules import OpenPypeModule, ITrayAction
from openpype.lib import run_detached_process, get_openpype_execute_args


class AssetReporterAction(OpenPypeModule, ITrayAction):

    label = "Asset Usage Report"
    name = "asset_reporter"

    def tray_init(self):
        pass

    def initialize(self, modules_settings):
        self.enabled = not AYON_SERVER_ENABLED

    def on_action_trigger(self):
        args = get_openpype_execute_args()
        args += ["run",
                 os.path.join(
                     os.path.dirname(__file__),
                     "window.py")]

        print(" ".join(args))
        run_detached_process(args)
