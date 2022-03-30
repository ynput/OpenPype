import os

import pyblish.api

from openpype.lib import get_subset_name_with_asset_doc


class CollectReview(pyblish.api.ContextPlugin):
    """Gather the active document as review instance."""

    label = "Review"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["photoshop"]

    def process(self, context):
        family = "review"
        subset = get_subset_name_with_asset_doc(
            family,
            "",
            context.data["anatomyData"]["task"]["name"],
            context.data["assetEntity"],
            context.data["anatomyData"]["project"]["name"],
            host_name=context.data["hostName"]
        )

        file_path = context.data["currentFile"]
        base_name = os.path.basename(file_path)

        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": base_name,
            "name": base_name,
            "family": family,
            "families": ["ftrack"],
            "representations": [],
            "asset": os.environ["AVALON_ASSET"]
        })
