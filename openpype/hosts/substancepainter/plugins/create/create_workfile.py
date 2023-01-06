# -*- coding: utf-8 -*-
"""Creator plugin for creating workfiles."""

from openpype.pipeline import CreatedInstance, AutoCreator
from openpype.pipeline import legacy_io
from openpype.client import get_asset_by_name

import substance_painter.project


def set_workfile_data(data, update=False):
    if update:
        data = get_workfile_data().update(data)
    metadata = substance_painter.project.Metadata("OpenPype")
    metadata.set("workfile", data)


def get_workfile_data():
    metadata = substance_painter.project.Metadata("OpenPype")
    return metadata.get("workfile") or {}


class CreateWorkfile(AutoCreator):
    """Workfile auto-creator."""
    identifier = "io.openpype.creators.substancepainter.workfile"
    label = "Workfile"
    family = "workfile"
    icon = "document"

    default_variant = "Main"

    def create(self):

        variant = self.default_variant
        project_name = self.project_name
        asset_name = legacy_io.Session["AVALON_ASSET"]
        task_name = legacy_io.Session["AVALON_TASK"]
        host_name = legacy_io.Session["AVALON_APP"]

        # Workfile instance should always exist and must only exist once.
        # As such we'll first check if it already exists and is collected.
        current_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ), None)

        if current_instance is None:
            self.log.info("Auto-creating workfile instance...")
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            data = {
                "asset": asset_name,
                "task": task_name,
                "variant": variant
            }
            current_instance = self.create_instance_in_context(subset_name,
                                                               data)
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

        set_workfile_data(current_instance.data_to_store())

    def collect_instances(self):
        workfile = get_workfile_data()
        if not workfile:
            return
        self.create_instance_in_context_from_existing(workfile)

    def update_instances(self, update_list):
        for instance, _changes in update_list:
            set_workfile_data(instance.data_to_store(), update=True)

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
