from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostModule


class OpenPypeMaya(OpenPypeModule, IHostModule):
    name = "openpype_maya"
    host_name = "maya"

    def initialize(self, module_settings):
        self.enabled = True
