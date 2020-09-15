import copy
import pyblish.api
from pprint import pformat


class CollectPsdInstances(pyblish.api.InstancePlugin):
    """
    Collect all available instances from psd batch.
    """

    label = "Collect Psd Instances"
    order = pyblish.api.CollectorOrder + 0.489
    hosts = ["standalonepublisher"]
    families = ["background_batch"]

    # presets
    subsets = {
        "backgroundLayout": {
            "task": "background",
            "family": "backgroundLayout"
        },
        "backgroundComp": {
            "task": "background",
            "family": "backgroundComp"
        },
        "workfileBackground": {
            "task": "background",
            "family": "workfile"
        }
    }
    unchecked_by_default = []

    def process(self, instance):
        context = instance.context
        asset_data = instance.data["assetEntity"]
        asset_name = instance.data["asset"]
        for subset_name, subset_data in self.subsets.items():
            instance_name = f"{asset_name}_{subset_name}"
            task = subset_data.get("task", "background")

            # create new instance
            new_instance = context.create_instance(instance_name)

            # add original instance data except name key
            for key, value in instance.data.items():
                if key not in ["name"]:
                    # Make sure value is copy since value may be object which
                    # can be shared across all new created objects
                    new_instance.data[key] = copy.deepcopy(value)

            # add subset data from preset
            new_instance.data.update(subset_data)

            new_instance.data["label"] = f"{instance_name}"
            new_instance.data["subset"] = subset_name
            new_instance.data["task"] = task


            if subset_name in self.unchecked_by_default:
                new_instance.data["publish"] = False

            self.log.info(f"Created new instance: {instance_name}")
            self.log.debug(f"_ inst_data: {pformat(new_instance.data)}")

        # delete original instance
        context.remove(instance)
