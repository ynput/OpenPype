# -*- coding: utf-8 -*-
"""Module providing support for Royal Render."""
import os
from openpype.modules import OpenPypeModule
from openpype_interfaces import IPluginPaths


class RoyalRenderModule(OpenPypeModule, IPluginPaths):
    """Class providing basic Royal Render implementation logic."""
    name = "royalrender"
    _api = None

    @property
    def api(self):
        if not self._api:
            # import royal render modules
            from . import api as rr_api
            self._api = rr_api.Api()

        return self._api

    def __init__(self, manager, settings):
        self.rr_paths = {}
        super(RoyalRenderModule, self).__init__(manager, settings)

    def initialize(self, module_settings):
        rr_settings = module_settings[self.name]
        self.enabled = rr_settings["enabled"]
        self.rr_paths = rr_settings.get("rr_paths")

    @staticmethod
    def get_plugin_paths(self):
        """Deadline plugin paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            "publish": [os.path.join(current_dir, "plugins", "publish")]
        }

