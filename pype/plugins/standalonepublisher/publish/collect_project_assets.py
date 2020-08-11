import pyblish.api
from avalon import io
from pprint import pformat


class CollectProjectAssets(pyblish.api.ContextPlugin):
    """
    Collect all available project assets to context data.
    """

    label = "Collect Project Assets"
    order = pyblish.api.CollectorOrder - 0.1
    hosts = ["standalonepublisher"]
    family = ["image"]

    def process(self, context):
        project_assets = {
            asset_doc["name"]: asset_doc
            for asset_doc in io.find({"type": "asset"})
        }
        context.data["projectAssets"] = project_assets
        self.log.debug(f"Collected project_assets: {pformat(project_assets)}")
