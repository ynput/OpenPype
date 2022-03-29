import os

import pyblish.api

from openpype.lib import get_subset_name


class CollectReview(pyblish.api.ContextPlugin):
    """Gather the active document as review instance."""

    label = "Review"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        family = "review"
        task = os.getenv("AVALON_TASK", None)
        subset = get_subset_name(
            family,
            "",
            task,
            context.data["assetEntity"]["_id"],
            host_name="photoshop"
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
