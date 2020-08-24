import copy
import glob
import os
from pprint import pformat

import pyblish.api


class CollectHarmonyScenes(pyblish.api.InstancePlugin):
    """Collect Harmony xstage files"""

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect Harmony Scene"
    hosts = ["standalonepublisher"]
    families = ["scene"]

    # presets
    subsets = {
        "sceneMain": {
            "family": "scene",
            "families": ["ftrack"],
            "extension": ".zip"
        },

    }

    def process(self, instance):
        context = instance.context
        asset_data = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        anatomy_data = instance.context.data["anatomyData"]
        repres = instance.data["representations"]
        staging_dir = repres[0]["stagingDir"]
        files = repres[0]["files"]
        provided_subset_name = instance.data.get("subset")

        if files.endswith(".zip"):
            for subset_name, subset_data in self.subsets.items():
                if provided_subset_name:
                    subset_name = provided_subset_name

                instance_name = f"{asset_name}_{subset_name}"

                task = instance.data.get("task", "sceneIngest")

                # updating hierarchy data
                anatomy_data.update({
                    "asset": asset_data["name"],
                    "task": task,
                    "subset": subset_name
                })

                instance.data["task"] = task
                instance.data["publish"] = True


