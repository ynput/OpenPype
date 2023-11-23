# -*- coding: utf-8 -*-
"""Creator plugin for creating workfiles."""

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline import CreatedInstance, AutoCreator
from openpype.client import get_asset_by_name

from openpype.hosts.substancepainter.api.pipeline import (
    set_instances,
    set_instance,
    get_instances
)

import substance_painter.project


class CreateWorkfile(AutoCreator):
    """Workfile auto-creator."""
    identifier = "io.openpype.creators.substancepainter.workfile"
    label = "Workfile"
    family = "workfile"
    icon = "document"

    default_variant = "Main"

    def create(self):

        if not substance_painter.project.is_open():
            return

        variant = self.default_variant
        project_name = self.project_name
        asset_name = self.create_context.get_current_asset_name()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        # Workfile instance should always exist and must only exist once.
        # As such we'll first check if it already exists and is collected.
        current_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ), None)

        if current_instance is None:
            current_instance_asset = None
        elif AYON_SERVER_ENABLED:
            current_instance_asset = current_instance["folderPath"]
        else:
            current_instance_asset = current_instance["asset"]

        if current_instance is None:
            self.log.info("Auto-creating workfile instance...")
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            data = {
                "task": task_name,
                "variant": variant
            }
            if AYON_SERVER_ENABLED:
                data["folderPath"] = asset_name
            else:
                data["asset"] = asset_name
            current_instance = self.create_instance_in_context(subset_name,
                                                               data)
        elif (
            current_instance_asset != asset_name
            or current_instance["task"] != task_name
        ):
            # Update instance context if is not the same
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            if AYON_SERVER_ENABLED:
                current_instance["folderPath"] = asset_name
            else:
                current_instance["asset"] = asset_name
            current_instance["task"] = task_name
            current_instance["subset"] = subset_name

        set_instance(
            instance_id=current_instance.get("instance_id"),
            instance_data=current_instance.data_to_store()
        )

    def collect_instances(self):
        for instance in get_instances():
            if (instance.get("creator_identifier") == self.identifier or
                    instance.get("family") == self.family):
                self.create_instance_in_context_from_existing(instance)

    def update_instances(self, update_list):
        instance_data_by_id = {}
        for instance, _changes in update_list:
            # Persist the data
            instance_id = instance.get("instance_id")
            instance_data = instance.data_to_store()
            instance_data_by_id[instance_id] = instance_data
        set_instances(instance_data_by_id, update=True)

    # Helper methods (this might get moved into Creator class)
    def create_instance_in_context(self, subset_name, data):
        instance = CreatedInstance(
            self.family, subset_name, data, self
        )
        self.create_context.creator_adds_instance(instance)
        return instance

    def create_instance_in_context_from_existing(self, data):
        instance = CreatedInstance.from_existing(data, self)
        self.create_context.creator_adds_instance(instance)
        return instance
