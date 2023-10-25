import re

from openpype import AYON_SERVER_ENABLED
import openpype.hosts.photoshop.api as api
from openpype.client import get_asset_by_name
from openpype.lib import prepare_template_data
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance
)
from openpype.hosts.photoshop.api.pipeline import cache_and_get_instances


class PSAutoCreator(AutoCreator):
    """Generic autocreator to extend."""
    def get_instance_attr_defs(self):
        return []

    def collect_instances(self):
        for instance_data in cache_and_get_instances(self):
            creator_id = instance_data.get("creator_identifier")

            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        self.log.debug("update_list:: {}".format(update_list))
        for created_inst, _changes in update_list:
            api.stub().imprint(created_inst.get("instance_id"),
                               created_inst.data_to_store())

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

        if existing_instance is None:
            existing_instance_asset = None
        elif AYON_SERVER_ENABLED:
            existing_instance_asset = existing_instance["folderPath"]
        else:
            existing_instance_asset = existing_instance["asset"]

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

            if not self.active_on_create:
                data["active"] = False

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)
            api.stub().imprint(new_instance.get("instance_id"),
                               new_instance.data_to_store())

        elif (
            existing_instance_asset != asset_name
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


def clean_subset_name(subset_name):
    """Clean all variants leftover {layer} from subset name."""
    dynamic_data = prepare_template_data({"layer": "{layer}"})
    for value in dynamic_data.values():
        if value in subset_name:
            subset_name = (subset_name.replace(value, "")
                                      .replace("__", "_")
                                      .replace("..", "."))
    # clean trailing separator as Main_
    pattern = r'[\W_]+$'
    replacement = ''
    return re.sub(pattern, replacement, subset_name)
