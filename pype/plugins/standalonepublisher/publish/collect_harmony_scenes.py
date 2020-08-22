
import os
import copy

import pyblish.api
import shutil

import pyblish.api
from avalon import io


class CollectHarmonyScenes(pyblish.api.InstancePlugin):
    """Collect Harmony xstage files"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Harmony Scene"
    hosts = ["standalonepublisher"]
    families = ["scene"]

    # presets
    subsets = {
        "sceneMain": {
            "family": "scene",
            "families": ["ftrack"],
            "extension": ".xstage"
        }
    }

    def process(self, instance):
        context = instance.context
        asset_doc = instance.data["assetEntity"]
        asset_name = instance.data["asset"]

        for subset_name, subset_data in self.subsets.items():
            instance_name = f"{asset_name}_{subset_name}"
            task = subset_data.get("task", "background")

            instance_name = subset_name = "sceneMain"

            new_instance = context.create_instance(instance_name)
            for key, value in instance.data.items():
                if key not in self.ignored_instance_data_keys:
                    new_instance.data[key] = copy.deepcopy(value)

            new_instance.data["label"] = " ".join(
                (new_instance.data["asset"], instance_name)
            )

            # Find latest version
            latest_version = self.find_last_version(subset_name, asset_doc)
            version_number = 1
            if latest_version is not None:
                version_number += latest_version

            self.log.info(
                "Next version of instance \"{}\" will be {}".format(
                    instance_name, version_number
                )
            )

            # Set family and subset
            new_instance.data["family"] = self.new_instance_family
            new_instance.data["subset"] = subset_name
            new_instance.data["version"] = version_number
            new_instance.data["latestVersion"] = latest_version

            new_instance.data["anatomyData"].update({
                "subset": subset_name,
                "family": self.new_instance_family,
                "version": version_number
            })

            # Copy `families` and check if `family` is not in current families
            families = new_instance.data.get("families") or list()
            if families:
                families = list(set(families))

            if self.new_instance_family in families:
                families.remove(self.new_instance_family)
            new_instance.data["families"] = families

            # Prepare staging dir for new instance
            staging_dir = self.staging_dir(new_instance)

            repres = instance.data.get("representations")
            source = os.path.join(repres[0]["stagingDir"], repres[0]["files"])

            os.chdir(os.path.dirname(source))
            zip_file = shutil.make_archive(
                os.path.basename(source), "zip", staging_dir)
            output_filename = os.path.basename(zip_file)

            new_repre = {
                "name": "zip",
                "ext": "zip",
                "files": output_filename,
                "stagingDir": staging_dir
            }
            self.log.debug(
                "Creating new representation: {}".format(new_repre)
            )
            new_instance.data["representations"] = [new_repre]

        # delete original instance
        context.remove(instance)