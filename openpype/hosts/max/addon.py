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

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(MAX_HOST_DIR, "hooks")
        ]
