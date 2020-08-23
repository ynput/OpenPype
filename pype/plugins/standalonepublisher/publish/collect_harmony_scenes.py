import copy
from pprint import pformat

import pyblish.api


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

    unchecked_by_default = []

    def process(self, instance):
        context = instance.context
        asset_data = instance.context.data["assetEntity"]
        asset_name = instance.data["asset"]
        anatomy_data = instance.context.data["anatomyData"]

        for subset_name, subset_data in self.subsets.items():
            instance_name = f"{asset_name}_{subset_name}"
            task = subset_data.get("task", "ingest")

            # create new instance
            new_instance = instance#context.create_instance(instance_name)

            # # add original instance data except name key
            # for key, value in instance.data.items():
            #     if key not in ["name"]:
            #         # Make sure value is copy since value may be object which
            #         # can be shared across all new created objects
            #         instance.data[key] = copy.deepcopy(value)

            # add subset data from preset
            instance.data.update(subset_data)

            instance.data["label"] = f"{instance_name}"
            instance.data["subset"] = subset_name

            # fix anatomy data
            anatomy_data_new = copy.deepcopy(anatomy_data)
            # updating hierarchy data
            anatomy_data_new.update({
                "asset": asset_data["name"],
                "task": task,
                "subset": subset_name
            })
            instance.data["anatomyData"] = anatomy_data_new

            if subset_name in self.unchecked_by_default:
                instance.data["publish"] = False

            self.log.info(f"Created new instance: {instance_name}")
            self.log.debug(f"_ inst_data: {pformat(instance.data)}")


