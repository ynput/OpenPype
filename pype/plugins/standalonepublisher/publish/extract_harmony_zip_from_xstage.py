import os
import pype.api
import copy
import os
import tempfile
import shutil

import pyblish.api
from avalon import io
from pprint import pformat


class ExtractHarmonyZipFromXstage(pype.api.Extractor):
    """Extract Harmony zip"""

    label = "Extract Shot Data"
    hosts = ["standalonepublisher"]
    families = ["review", "audio"]

    # presets

    def process(self, instance):
        context = instance.context
        asset_doc = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        subset_name = instance.data["subset"]
        instance_name = instance.data["name"]
        family = instance.data["family"]

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
        instance.data["family"] = family
        instance.data["subset"] = subset_name
        instance.data["version"] = version_number
        instance.data["latestVersion"] = latest_version

        instance.data["anatomyData"].update({
            "subset": subset_name,
            "family": family ,
            "version": version_number
        })

        # Copy `families` and check if `family` is not in current families
        families = instance.data.get("families") or list()
        if families:
            families = list(set(families))

        if self.instance_family in families:
            families.remove(self.instance_family)
        instance.data["families"] = families

        # Prepare staging dir for new instance
        staging_dir = self.staging_dir(instance)

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
        instance.data["representations"] = [new_repre]


    def find_last_version(self, subset_name, asset_doc):
        subset_doc = io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_doc["_id"]
        })

        if subset_doc is None:
            self.log.debug("Subset entity does not exist yet.")
        else:
            version_doc = io.find_one(
                {
                    "type": "version",
                    "parent": subset_doc["_id"]
                },
                sort=[("name", -1)]
            )
            if version_doc:
                return int(version_doc["name"])
        return None
