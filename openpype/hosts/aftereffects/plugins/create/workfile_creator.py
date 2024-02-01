from openpype import AYON_SERVER_ENABLED
import openpype.hosts.aftereffects.api as api
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance
)
from openpype.hosts.aftereffects.api.pipeline import cache_and_get_instances


class AEWorkfileCreator(AutoCreator):
    identifier = "workfile"
    family = "workfile"

    default_variant = "Main"

    def get_instance_attr_defs(self):
        return []

    def collect_instances(self):
        for instance_data in cache_and_get_instances(self):
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

        context = self.create_context
        project_name = context.get_current_project_name()
        asset_name = context.get_current_asset_name()
        task_name = context.get_current_task_name()
        host_name = context.host_name

        existing_asset_name = None
        if existing_instance is not None:
            if AYON_SERVER_ENABLED:
                existing_asset_name = existing_instance.get("folderPath")

            if existing_asset_name is None:
                existing_asset_name = existing_instance["asset"]

        if existing_instance is None:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                self.default_variant, task_name, asset_doc,
                project_name, host_name
            )
            data = {
                "task": task_name,
                "variant": self.default_variant
            }
            if AYON_SERVER_ENABLED:
                data["folderPath"] = asset_name
            else:
                data["asset"] = asset_name
            data.update(self.get_dynamic_data(
                self.default_variant, task_name, asset_doc,
                project_name, host_name, None
            ))

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)

            api.get_stub().imprint(new_instance.get("instance_id"),
                                   new_instance.data_to_store())

        elif (
            existing_asset_name != asset_name
            or existing_instance["task"] != task_name
        ):
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                self.default_variant, task_name, asset_doc,
                project_name, host_name
            )
            if AYON_SERVER_ENABLED:
                existing_instance["folderPath"] = asset_name
            else:
                existing_instance["asset"] = asset_name

            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name
