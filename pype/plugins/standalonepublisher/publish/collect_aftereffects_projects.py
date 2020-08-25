import copy
import glob
import os
from pprint import pformat

import pyblish.api


class CollectAftereffectsProjects(pyblish.api.InstancePlugin):
    """Collect After Effects Projects"""

    order = pyblish.api.CollectorOrder + 0.498
    label = "Collect After Effects Projects"
    hosts = ["standalonepublisher"]
    families = ["scene"]

    # presets
    subsets = {
        "sceneMain": {
            "family": "scene",
            "families": ["ftrack"],
            "extension": ".aex"
        },
    }
    extensions = [".aex"]
    ignored_instance_data_keys = ("name", "label", "stagingDir", "version")

    def process(self, instance):
        context = instance.context
        asset_data = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        anatomy_data = instance.context.data["anatomyData"]
        repres = instance.data["representations"]
        staging_dir = repres[0]["stagingDir"]
        files = repres[0]["files"]

        if files.endswith(".aex"):

            # A folder or xstage was dropped
            for subset_name, subset_data in self.subsets.items():
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
                # add subset data from preset
                new_instance.data.update(subset_data)

                new_instance.data["label"] = f"{instance_name}"
                new_instance.data["subset"] = subset_name

                # fix anatomy data
                anatomy_data_new = copy.deepcopy(anatomy_data)
                # updating hierarchy data
                anatomy_data_new.update({
                    "asset": asset_data["name"],
                    "task": task,
                    "subset": subset_name
                })

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
