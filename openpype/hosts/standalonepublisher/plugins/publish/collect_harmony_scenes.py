# -*- coding: utf-8 -*-
"""Collect Harmony scenes in Standalone Publisher."""
import copy
import glob
import os
from pprint import pformat

import pyblish.api


class CollectHarmonyScenes(pyblish.api.InstancePlugin):
    """Collect Harmony xstage files."""

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect Harmony Scene"
    hosts = ["standalonepublisher"]
    families = ["harmony.scene"]

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
        staging_dir = repres[0]["stagingDir"]
        files = repres[0]["files"]

        if not files.endswith(".zip"):
            # A harmony project folder / .xstage was dropped
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

            # fix anatomy data
            anatomy_data_new = copy.deepcopy(anatomy_data)

            project_entity = context.data["projectEntity"]
            asset_entity = context.data["assetEntity"]

            task_type = asset_entity["data"]["tasks"].get(task, {}).get("type")
            project_task_types = project_entity["config"]["tasks"]
            task_code = project_task_types.get(task_type, {}).get("short_name")

            # updating hierarchy data
            anatomy_data_new.update({
                "asset": asset_data["name"],
                "task": {
                    "name": task,
                    "type": task_type,
                    "short": task_code,
                },
                "subset": subset_name
            })

            new_instance.data["label"] = f"{instance_name}"
            new_instance.data["subset"] = subset_name
            new_instance.data["extension"] = ".zip"
            new_instance.data["anatomyData"] = anatomy_data_new
            new_instance.data["publish"] = True

            # When a project folder was dropped vs. just an xstage file, find
            # the latest file xstage version and update the instance
            if not files.endswith(".xstage"):

                source_dir = os.path.join(
                    staging_dir, files
                ).replace("\\", "/")

                latest_file = max(glob.iglob(source_dir + "/*.xstage"),
                                  key=os.path.getctime).replace("\\", "/")

                new_instance.data["representations"][0]["stagingDir"] = (
                    source_dir
                )
                new_instance.data["representations"][0]["files"] = (
                    os.path.basename(latest_file)
                )
            self.log.info(f"Created new instance: {instance_name}")
            self.log.debug(f"_ inst_data: {pformat(new_instance.data)}")

        # set original instance for removal
        self.log.info("Context data: {}".format(context.data))
        instance.data["remove"] = True
