# -*- coding: utf-8 -*-
"""Module providing support for Royal Render."""
import os
import openpype.modules
from openpype.modules import OpenPypeModule, IPluginPaths
from openpype import AYON_SERVER_ENABLED
from openpype.lib import Logger



class RoyalRenderModule(OpenPypeModule, IPluginPaths):
    """Class providing basic Royal Render implementation logic."""
    name = "royalrender"

    @property
    def api(self):
        if not self._api:
            # import royal render modules
            from . import api as rr_api
            self._api = rr_api.Api(self.settings)

        return self._api

    def __init__(self, manager, settings):
        # type: (openpype.modules.base.ModulesManager, dict) -> None
        self.rr_paths = {}
        self._api = None
        self.settings = settings
        super(RoyalRenderModule, self).__init__(manager, settings)

    def initialize(self, module_settings):
        # type: (dict) -> None
        rr_settings = module_settings[self.name]
        self.enabled = rr_settings["enabled"]
        self.rr_paths = rr_settings.get("rr_paths")

        # Ayon only
        if not AYON_SERVER_ENABLED:
            self.log.info("RoyalRender is not implemented for Openpype")
            self.enabled = False

    @staticmethod
    def get_plugin_paths():
        # type: () -> dict
        """Royal Render plugin paths.

        Returns:
            dict: Dictionary of plugin paths for RR.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            "publish": [os.path.join(current_dir, "plugins", "publish")]
        }
