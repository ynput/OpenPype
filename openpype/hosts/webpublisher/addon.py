import os
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostModule

WEBPUBLISHER_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class WebpublisherAddon(OpenPypeModule, IHostModule):
    name = "webpublisher"
    host_name = "webpublisher"

    def initialize(self, module_settings):
        self.enabled = True
