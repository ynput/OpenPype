# -*- coding: utf-8 -*-
"""Creator plugin for creating workfiles."""
from openpype.hosts.houdini.api import plugin
from openpype.hosts.houdini.api.lib import read
from openpype.pipeline import CreatedInstance, AutoCreator
from openpype.pipeline.legacy_io import Session
from openpype.client import get_asset_by_name


class CreateWorkfile(plugin.HoudiniCreatorBase, AutoCreator):
    """Workfile auto-creator."""
    identifier = "io.openpype.creators.houdini.workfile"
    label = "Workfile"
    family = "workfile"
    icon = "gears"

    default_variant = "Main"

    def create(self):
        variant = self.default_variant
        current_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ), None)

        project_name = self.project_name
        asset_name = Session["AVALON_ASSET"]
        task_name = Session["AVALON_TASK"]
        host_name = Session["AVALON_APP"]

        if current_instance is None:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            data = {
                "asset": asset_name,
                "task": task_name,
                "variant": variant
            }
            data.update(
                self.get_dynamic_data(
                    variant, task_name, asset_doc,
                    project_name, host_name, current_instance)
            )

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)

            # Update instance context if is not the same
        elif (
                current_instance["asset"] != asset_name
                or current_instance["task"] != task_name
        ):
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                variant, task_name, asset_doc, project_name, host_name
            )
            current_instance["asset"] = asset_name
            current_instance["task"] = task_name
            current_instance["subset"] = subset_name

    def collect_instances(self):
        self.cache_instances(self.collection_shared_data)
        for instance in self.collection_shared_data["houdini_cached_instances"].get(self.identifier, []):  # noqa
            created_instance = CreatedInstance.from_existing(
                read(instance), self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        pass

