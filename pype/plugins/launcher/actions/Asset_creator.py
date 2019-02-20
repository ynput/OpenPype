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
    icon = "retweet"
    order = 250

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""

        return True

    def process(self, session, **kwargs):
        return lib.launch(executable="python",
                          args=["-u", "-m", "pype.tools.assetcreator",
                                session['AVALON_PROJECT']])
