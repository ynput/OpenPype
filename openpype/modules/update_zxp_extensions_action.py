import os

from openpype import AYON_SERVER_ENABLED
from openpype.modules import OpenPypeModule, ITrayAction
from openpype.settings import get_system_settings

import igniter  # noqa: E402
from igniter import BootstrapRepos  # noqa: E402


class UpdateZXPExtensionsAction(OpenPypeModule, ITrayAction):
    name = "update_zxp_extensions"
    label = "Update ZXP Extensions"
    submenu = "More Tools"

    def __init__(self, manager, settings):
        super().__init__(manager, settings)

    def initialize(self, _modules_settings):
        self.enabled = True
        if AYON_SERVER_ENABLED:
            self.enabled = False

    def tray_init(self):
        return

    def tray_start(self):
        return

    def tray_exit(self):
        return

    def on_action_trigger(self):
        # install latest version to user data dir
        bootstrap = BootstrapRepos()

        openpype_version = bootstrap.find_openpype_version(os.environ["OPENPYPE_VERSION"])

        system_settings = get_system_settings()
        zxp_hosts_to_update = bootstrap.get_zxp_extensions_to_update(openpype_version, system_settings, force=True)
        igniter.open_update_window(openpype_version, zxp_hosts_to_update)
