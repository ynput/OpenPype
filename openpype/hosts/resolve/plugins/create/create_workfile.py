# -*- coding: utf-8 -*-
"""Creator plugin for creating workfiles."""
from openpype.pipeline import CreatedInstance, AutoCreator
from openpype.client import get_asset_by_name


class CreateWorkfile(AutoCreator):
    """Workfile auto-creator."""
    identifier = "io.openpype.creators.resolve.workfile"
    label = "Workfile"
    family = "workfile"
    icon = "fa5.file"

    default_variant = "Main"

    def create(self):

        variant = self.default_variant
        current_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ), None)

        project_name = self.project_name
        asset_name = self.create_context.get_current_asset_name()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        if current_instance is None:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            data = {
                "asset": asset_name,
                "task": task_name,
                "variant": variant,
            }
            data.update(
                self.get_dynamic_data(
                    variant, task_name, asset_doc,
                    project_name, host_name, current_instance)
            )
            self.log.info("Auto-creating workfile instance...")
            current_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(current_instance)
        elif (
                current_instance["asset"] != asset_name
                or current_instance["task"] != task_name
        ):
            # Update instance context if is not the same
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            current_instance["asset"] = asset_name
            current_instance["task"] = task_name
            current_instance["subset"] = subset_name

    def collect_instances(self):
        # TODO: Implement
        pass

    def update_instances(self, update_list):
        # TODO: Implement
        #   This needs to be implemented to allow persisting any instance
        #   data on resets. We'll need to decicde where to store workfile
        #   instance data reliably. Likely metadata on the *current project*?
        pass
