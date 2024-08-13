import os
import socket

from openpype import resources
from openpype.modules import OpenPypeModule, ITrayService


class PortainerModule(OpenPypeModule, ITrayService):
    name = "portainer"
    label = "Portainer"

    def initialize(self, _module_settings):
        self.enabled = True