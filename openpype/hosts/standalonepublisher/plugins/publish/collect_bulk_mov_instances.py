import copy
import json
import pyblish.api

from openpype.lib import get_subset_name_with_asset_doc
from openpype.pipeline import legacy_io


class CollectBulkMovInstances(pyblish.api.InstancePlugin):
    """Collect all available instances for batch publish."""

    label = "Collect Bulk Mov Instances"
    order = pyblish.api.CollectorOrder + 0.489
    hosts = ["standalonepublisher"]
    families = ["render_mov_batch"]

    new_instance_family = "render"
    instance_task_names = [
        "compositing",
        "comp"
    ]
    default_task_name = "compositing"
    subset_name_variant = "Default"

    def process(self, instance):
        context = instance.context
        asset_name = instance.data["asset"]

        asset_doc = legacy_io.find_one({
            "type": "asset",
            "name": asset_name
        })
        if not asset_doc:
            raise AssertionError((
                "Couldn't find Asset document with name \"{}\""
            ).format(asset_name))

        available_task_names = {}
        asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
        for task_name in asset_tasks.keys():
            available_task_names[task_name.lower()] = task_name

        task_name = self.default_task_name
        for _task_name in self.instance_task_names:
            _task_name_low = _task_name.lower()
            if _task_name_low in available_task_names:
                task_name = available_task_names[_task_name_low]
                break

        subset_name = get_subset_name_with_asset_doc(
            self.new_instance_family,
            self.subset_name_variant,
            task_name,
            asset_doc,
            legacy_io.Session["AVALON_PROJECT"]
        )
        instance_name = f"{asset_name}_{subset_name}"

        # create new instance
        new_instance = context.create_instance(instance_name)
        new_instance_data = {
            "name": instance_name,
            "label": instance_name,
            "family": self.new_instance_family,
            "subset": subset_name,
            "task": task_name
        }
        new_instance.data.update(new_instance_data)
        # add original instance data except name key
        for key, value in instance.data.items():
            if key in new_instance_data:
                continue
            # Make sure value is copy since value may be object which
            # can be shared across all new created objects
            new_instance.data[key] = copy.deepcopy(value)

        # Add `render_mov_batch` for specific validators
        if "families" not in new_instance.data:
            new_instance.data["families"] = []
        new_instance.data["families"].append("render_mov_batch")

        # delete original instance
        context.remove(instance)

        self.log.info(f"Created new instance: {instance_name}")

        def convertor(value):
            return str(value)

        self.log.debug("Instance data: {}".format(
            json.dumps(new_instance.data, indent=4, default=convertor)
        ))
