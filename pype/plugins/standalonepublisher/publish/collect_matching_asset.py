import os
import pyblish.api
from pprint import pformat


class CollectMatchingAssetToInstance(pyblish.api.InstancePlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Matching Asset to Instance"
    order = pyblish.api.CollectorOrder - 0.05
    hosts = ["standalonepublisher"]
    family = ["image"]

    def process(self, instance):
        project_assets = instance.context.data["projectAssets"]
        source_file = os.path.basename(instance.data["source"])
        asset = next((project_assets[name] for name in project_assets
                      if name in source_file), None)

        if asset:
            instance.data["asset"] = asset["name"]
            instance.data["assetEntity"] = asset
            self.log.info(f"Matching asset assigned: {pformat(asset)}")
