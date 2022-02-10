from openpype.hosts.testhost.api import pipeline
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
    lib
)
from avalon import io


class MyAutoCreator(AutoCreator):
    identifier = "workfile"
    family = "workfile"

    def get_instance_attr_defs(self):
        output = [
            lib.NumberDef("number_key", label="Number")
        ]
        return output

    def collect_instances(self):
        for instance_data in pipeline.list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                subset_name = instance_data["subset"]
                instance = CreatedInstance(
                    self.family, subset_name, instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        pipeline.update_instances(update_list)

    def create(self, options=None):
        existing_instance = None
        for instance in self.create_context.instances:
            if instance.family == self.family:
                existing_instance = instance
                break

        variant = "Main"
        project_name = io.Session["AVALON_PROJECT"]
        asset_name = io.Session["AVALON_ASSET"]
        task_name = io.Session["AVALON_TASK"]
        host_name = io.Session["AVALON_APP"]

        if existing_instance is None:
            asset_doc = io.find_one({"type": "asset", "name": asset_name})
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            data = {
                "asset": asset_name,
                "task": task_name,
                "variant": variant
            }
            data.update(self.get_dynamic_data(
                variant, task_name, asset_doc, project_name, host_name
            ))

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)

        elif (
            existing_instance["asset"] != asset_name
            or existing_instance["task"] != task_name
        ):
            asset_doc = io.find_one({"type": "asset", "name": asset_name})
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
