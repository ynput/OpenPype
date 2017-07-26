import json
import os
import shutil

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ExtractTextures(colorbleed.api.Extractor):

    label = "Extract Textures"
    hosts = ["maya"]
    families = ["colorbleed.texture"]
    order = pyblish.api.ExtractorOrder + 0.1

    def process(self, instance):

        self.log.info("Extracting textures ...")

        dir_path = self.staging_dir(instance)
        resources = instance.data["resources"]
        for resource in resources:
            self.copy_files(dir_path, resource["files"])

        self.log.info("Storing cross instance information ...")
        self.store_data(resources)

    def store_data(self, data):
        tmp_dir = lib.maya_temp_folder()
        tmp_file = os.path.join(tmp_dir, "resources.json")
        with open(tmp_file, "w") as f:
            json.dump(data, fp=f,
                      separators=[",", ":"],
                      ensure_ascii=False)

    def copy_files(self, dest, files):
        for f in files:
            fname = os.path.basename(f)
            dest_file = os.path.join(dest, fname)
            shutil.copy(f, dest_file)
