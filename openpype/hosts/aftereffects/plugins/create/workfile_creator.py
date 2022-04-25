import openpype.hosts.aftereffects.api as api
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
    legacy_io,
)


class AEWorkfileCreator(AutoCreator):
    identifier = "workfile"
    family = "workfile"

    def get_instance_attr_defs(self):
        return []

    def collect_instances(self):
        for instance_data in api.list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                subset_name = instance_data["subset"]
                instance = CreatedInstance(
                    self.family, subset_name, instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        # nothing to change on workfiles
        pass

    def create(self, options=None):
        existing_instance = None
        for instance in self.create_context.instances:
            if instance.family == self.family:
                existing_instance = instance
                break

        variant = ''
        project_name = legacy_io.Session["AVALON_PROJECT"]
        asset_name = legacy_io.Session["AVALON_ASSET"]
        task_name = legacy_io.Session["AVALON_TASK"]
        host_name = legacy_io.Session["AVALON_APP"]

        if existing_instance is None:
            asset_doc = legacy_io.find_one({"type": "asset", "name": asset_name})
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

            api.get_stub().imprint(new_instance.get("instance_id"),
                                   new_instance.data_to_store())

        elif (
            existing_instance["asset"] != asset_name
            or existing_instance["task"] != task_name
        ):
            asset_doc = legacy_io.find_one({
                "type": "asset",
                "name": asset_name
            })
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
