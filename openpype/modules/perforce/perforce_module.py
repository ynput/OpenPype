from openpype.modules import OpenPypeModule, ITrayService
from openpype.modules.perforce.rest_api import PerforceModuleRestAPI


class PerforceModule(OpenPypeModule, ITrayService):
    name = "perforce"
    label = "Perforce"

    def initialize(self, module_settings):
        self.enabled = module_settings[self.name]["enabled"]
        self.server_manager = None

    def webserver_initialization(self, server_manager):
        """Add routes for syncs."""
        if self.tray_initialized:
            self.rest_api_obj = PerforceModuleRestAPI(
                self, server_manager
            )

    def tray_init(self):
        pass

    def tray_start(self):
        pass

    def tray_exit(self):
        pass
