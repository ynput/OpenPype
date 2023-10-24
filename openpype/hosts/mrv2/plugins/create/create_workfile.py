import json

from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
)

from mrv2 import session


class FusionWorkfileCreator(AutoCreator):
    identifier = "workfile"
    family = "workfile"
    label = "Workfile"
    icon = "fa5.file"

    default_variant = "Main"

    create_allow_context_change = False

    data_key = "ayon_workfile"

    def collect_instances(self):
        data = session.metadata(self.data_key)
        if not data:
            return

        try:
            data = json.loads(data)
        except json.decoder.JSONDecodeError as exc:
            self.log.info(exc, exc_info=True)
            return

        instance = CreatedInstance(
            family=self.family,
            subset_name=data["subset"],
            data=data,
            creator=self
        )

        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            data = created_inst.data_to_store()
            session.setMetadata(self.data_key, json.dumps(data))

    def create(self, options=None):

        existing_instance = None
        for instance in self.create_context.instances:
            if instance.family == self.family:
                existing_instance = instance
                break

        project_name = self.create_context.get_current_project_name()
        asset_name = self.create_context.get_current_asset_name()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        if existing_instance is None:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                self.default_variant, task_name, asset_doc,
                project_name, host_name
            )
            data = {
                "asset": asset_name,
                "task": task_name,
                "variant": self.default_variant
            }
            data.update(self.get_dynamic_data(
                self.default_variant, task_name, asset_doc,
                project_name, host_name, None
            ))

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)

        elif (
            existing_instance["asset"] != asset_name
            or existing_instance["task"] != task_name
        ):
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                self.default_variant, task_name, asset_doc,
                project_name, host_name
            )
            existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name
