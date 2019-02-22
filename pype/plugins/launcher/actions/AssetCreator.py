import os
import sys
import acre

from avalon import api, lib
from pype.tools import assetcreator

from pype.api import Logger

log = Logger.getLogger(__name__, "aport")


class AssetCreator(api.Action):

    name = "asset_creator"
    label = "Asset Creator"
    icon = "plus-square"
    order = 250

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_PROJECT" in session:
            return True
        return False

    def process(self, session, **kwargs):
        asset = ''
        if 'AVALON_ASSET' in session:
            asset = session['AVALON_ASSET']
        return lib.launch(
            executable="python",
            args=[
                "-u", "-m", "pype.tools.assetcreator",
                session['AVALON_PROJECT'], asset
            ]
        )
