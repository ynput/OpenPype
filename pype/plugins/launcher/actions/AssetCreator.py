from avalon import api, lib

from pype.api import Logger

log = Logger().get_logger(__name__, "asset_creator")


class AssetCreator(api.Action):

    name = "asset_creator"
    label = "Asset Creator"
    icon = "plus-square"
    order = 250

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        compatible = True

        # Check required modules.
        module_names = [
            "ftrack_api", "ftrack_api_old", "pype.tools.assetcreator"
        ]
        for name in module_names:
            try:
                __import__(name)
            except ImportError:
                compatible = False

        # Check session environment.
        if "AVALON_PROJECT" not in session:
            compatible = False

        return compatible

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
