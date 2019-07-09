import nuke
from avalon import api, io
import pyblish.api


class CollectAssetInfo(pyblish.api.ContextPlugin):
    """Collect framerate."""

    order = pyblish.api.CollectorOrder
    label = "Collect Asset Info"
    hosts = [
        "nuke",
        "nukeassist"
    ]

    def process(self, context):
        asset_data = io.find_one({"type": "asset",
                                  "name": api.Session["AVALON_ASSET"]})
        self.log.info("asset_data: {}".format(asset_data))

        context.data['handles'] = int(asset_data["data"].get("handles", 0))
