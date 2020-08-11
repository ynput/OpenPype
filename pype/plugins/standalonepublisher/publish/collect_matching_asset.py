import os
import pyblish.api
from avalon import io
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
        source_file = os.path.basename(instance.data["source"])
        self.log.info("Looking for asset document for file \"{}\"".format(
            instance.data["source"]
        ))

        project_assets = instance.context.data["projectAssets"]
        matching_asset_doc = project_assets.get(source_file)
        if matching_asset_doc is None:
            for asset_doc in project_assets.values():
                if asset_doc["name"] in source_file:
                    matching_asset_doc = asset_doc
                    break

        if not matching_asset_doc:
            # TODO better error message
            raise AssertionError((
                "Filename does not contain any name of"
                " asset documents in database."
            ))

        instance.data["asset"] = matching_asset_doc["name"]
        instance.data["assetEntity"] = matching_asset_doc
        self.log.info(
            f"Matching asset found: {pformat(matching_asset_doc)}"
        )
