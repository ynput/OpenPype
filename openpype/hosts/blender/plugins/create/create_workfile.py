import bpy

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline import CreatedInstance, AutoCreator
from openpype.client import get_asset_by_name
from openpype.hosts.blender.api.plugin import BaseCreator
from openpype.hosts.blender.api.pipeline import (
    AVALON_PROPERTY,
    AVALON_CONTAINERS
)


class CreateWorkfile(BaseCreator, AutoCreator):
    """Workfile auto-creator.

    The workfile instance stores its data on the `AVALON_CONTAINERS` collection
    as custom attributes, because unlike other instances it doesn't have an
    instance node of its own.

    """
    identifier = "io.openpype.creators.blender.workfile"
    label = "Workfile"
    family = "workfile"
    icon = "fa5.file"

    def create(self):
        """Create workfile instances."""
        workfile_instance = next(
            (
                instance for instance in self.create_context.instances
                if instance.creator_identifier == self.identifier
            ),
            None,
        )

        project_name = self.project_name
        asset_name = self.create_context.get_current_asset_name()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        existing_asset_name = None
        if workfile_instance is not None:
            if AYON_SERVER_ENABLED:
                existing_asset_name = workfile_instance.get("folderPath")

            if existing_asset_name is None:
                existing_asset_name = workfile_instance["asset"]

        if not workfile_instance:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                task_name, task_name, asset_doc, project_name, host_name
            )
            data = {
                "task": task_name,
                "variant": task_name,
            }
            if AYON_SERVER_ENABLED:
                data["folderPath"] = asset_name
            else:
                data["asset"] = asset_name
            data.update(
                self.get_dynamic_data(
                    task_name,
                    task_name,
                    asset_doc,
                    project_name,
                    host_name,
                    workfile_instance,
                )
            )
            self.log.info("Auto-creating workfile instance...")
            workfile_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(workfile_instance)

        elif (
            existing_asset_name != asset_name
            or workfile_instance["task"] != task_name
        ):
            # Update instance context if it's different
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                task_name, task_name, asset_doc, project_name, host_name
            )
            if AYON_SERVER_ENABLED:
                workfile_instance["folderPath"] = asset_name
            else:
                workfile_instance["asset"] = asset_name

            workfile_instance["task"] = task_name
            workfile_instance["subset"] = subset_name

        instance_node = bpy.data.collections.get(AVALON_CONTAINERS)
        if not instance_node:
            instance_node = bpy.data.collections.new(name=AVALON_CONTAINERS)
        workfile_instance.transient_data["instance_node"] = instance_node

    def collect_instances(self):

        instance_node = bpy.data.collections.get(AVALON_CONTAINERS)
        if not instance_node:
            return

        property = instance_node.get(AVALON_PROPERTY)
        if not property:
            return

        # Create instance object from existing data
        instance = CreatedInstance.from_existing(
            instance_data=property.to_dict(),
            creator=self
        )
        instance.transient_data["instance_node"] = instance_node

        # Add instance to create context
        self._add_instance_to_context(instance)

    def remove_instances(self, instances):
        for instance in instances:
            node = instance.transient_data["instance_node"]
            del node[AVALON_PROPERTY]

            self._remove_instance_from_context(instance)
