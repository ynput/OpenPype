# -*- coding: utf-8 -*-
"""Collect zips as Harmony scene files."""
import copy
from pprint import pformat

import pyblish.api


class CollectHarmonyZips(pyblish.api.InstancePlugin):
    """Collect Harmony zipped projects."""

    order = pyblish.api.CollectorOrder + 0.497
    label = "Collect Harmony Zipped Projects"
    hosts = ["standalonepublisher"]
    families = ["harmony.scene"]
    extensions = ["zip"]

    # presets
    ignored_instance_data_keys = ("name", "label", "stagingDir", "version")

    def process(self, instance):
        """Plugin entry point."""
        context = instance.context
        asset_data = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        subset_name = instance.data.get("subset", "sceneMain")
        anatomy_data = instance.context.data["anatomyData"]
        repres = instance.data["representations"]
        files = repres[0]["files"]
        project_entity = context.data["projectEntity"]

        if files.endswith(".zip"):
            # A zip file was dropped
            instance_name = f"{asset_name}_{subset_name}"
            task = instance.data.get("task", "harmonyIngest")

            # create new instance
            new_instance = context.create_instance(instance_name)

            # add original instance data except name key
            for key, value in instance.data.items():
                # Make sure value is copy since value may be object which
                # can be shared across all new created objects
                if key not in self.ignored_instance_data_keys:
                    new_instance.data[key] = copy.deepcopy(value)

            self.log.info("Copied data: {}".format(new_instance.data))

            task_type = asset_data["data"]["tasks"].get(task, {}).get("type")
            project_task_types = project_entity["config"]["tasks"]
            task_code = project_task_types.get(task_type, {}).get("short_name")

            # fix anatomy data
            anatomy_data_new = copy.deepcopy(anatomy_data)
            # updating hierarchy data
            anatomy_data_new.update(
                {
                    "asset": asset_data["name"],
                    "task": {
                        "name": task,
                        "type": task_type,
                        "short": task_code,
                    },
                    "subset": subset_name
                }
            )

            new_instance.data["label"] = f"{instance_name}"
            new_instance.data["subset"] = subset_name
            new_instance.data["extension"] = ".zip"
            new_instance.data["anatomyData"] = anatomy_data_new
            new_instance.data["publish"] = True

            self.log.info(f"Created new instance: {instance_name}")
            self.log.debug(f"_ inst_data: {pformat(new_instance.data)}")

        # set original instance for removal
        self.log.info("Context data: {}".format(context.data))
        instance.data["remove"] = True
