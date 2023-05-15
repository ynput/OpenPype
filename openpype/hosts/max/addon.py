# -*- coding: utf-8 -*-
import os
from openpype.modules import OpenPypeModule, IHostAddon

MAX_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class MaxAddon(OpenPypeModule, IHostAddon):
    name = "max"
    host_name = "max"

    def initialize(self, module_settings):
        self.enabled = True

    def get_workfile_extensions(self):
        return [".max"]
