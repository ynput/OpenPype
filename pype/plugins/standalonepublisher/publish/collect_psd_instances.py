import pyblish.api
from pprint import pformat


class CollectPsdInstances(pyblish.api.InstancePlugin):
    """
    Collect all available instances from psd batch.
    """

    label = "Collect Psd Instances"
    order = pyblish.api.CollectorOrder + 0.492
    hosts = ["standalonepublisher"]
    families = ["psd_batch"]

    # presets
    subsets = {
        "imageForLayout": {
            "task": "background",
            "family": "imageForLayout"
        },
        "imageForComp": {
            "task": "background",
            "family": "imageForComp"
        },
        "workfileBackground": {
            "task": "background",
            "family": "workfile"
        },
    }

    def process(self, instance):
        context = instance.context
        asset_data = instance.data["assetEntity"]
        asset = instance.data["asset"]
        anatomy_data = instance.data["anatomyData"].copy()

        for subset_name, subset_data in self.subsets.items():
            instance_name = f"{asset}_{subset_name}"
            task = subset_data.get("task", "background")

            # create new instance
            new_instance = context.create_instance(instance_name)
            # add original instance data except name key
            new_instance.data.update({k: v for k, v in instance.data.items()
                                      if k not in "name"})
            # add subset data from preset
            new_instance.data.update(subset_data)

            label = f"{instance_name}"
            new_instance.data["label"] = label
            new_instance.data["subset"] = subset_name
            new_instance.data["families"].append("image")

            # fix anatomy data
            anatomy_data_new = anatomy_data.copy()
            # updating hierarchy data
            anatomy_data_new.update({
                "asset": asset_data["name"],
                "task": task,
                "subset": subset_name
            })
            new_instance.data["anatomyData"] = anatomy_data_new

            inst_data = new_instance.data
            self.log.debug(
                f"_ inst_data: {pformat(inst_data)}")

            self.log.info(f"Created new instance: {instance_name}")

        # delete original instance
        context.remove(instance)
