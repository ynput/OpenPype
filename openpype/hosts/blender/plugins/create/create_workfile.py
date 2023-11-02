import bpy

from openpype.pipeline import CreatedInstance, AutoCreator
from openpype.client import get_asset_by_name
from openpype.hosts.blender.api.plugin import BaseCreator
from openpype.hosts.blender.api.lib import imprint
from openpype.hosts.blender.api.pipeline import AVALON_PROPERTY


class CreateWorkfile(BaseCreator, AutoCreator):
    """Workfile auto-creator."""
    identifier = "io.openpype.creators.blender.workfile"
    label = "Workfile"
    family = "workfile"
    icon = "fa5.file"

    def create(self):
        """Create workfile instances."""
        current_instance = next(
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

        if not current_instance:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                task_name, task_name, asset_doc, project_name, host_name
            )
            data = {
                "asset": asset_name,
                "task": task_name,
                "variant": task_name,
            }
            data.update(
                self.get_dynamic_data(
                    task_name,
                    task_name,
                    asset_doc,
                    project_name,
                    host_name,
                    current_instance,
                )
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
            # Update instance context if it's different
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                task_name, task_name, asset_doc, project_name, host_name
            )

            current_instance.update(
                {
                    "asset": asset_name,
                    "task": task_name,
                    "subset": subset_name,
                }
            )

    def collect_instances(self):
        """Collect workfile instances."""
        self.cache_subsets(self.collection_shared_data)
        cached_subsets = self.collection_shared_data["blender_cached_subsets"]
        for node in cached_subsets.get(self.identifier, []):
            created_instance = CreatedInstance.from_existing(
                self.read_instance_node(node), self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        """Update workfile instances."""
        for created_inst, _changes in update_list:
            data = created_inst.data_to_store()
            node = data.get("instance_node")
            if not node:
                task_name = self.create_context.get_current_task_name()

                bpy.context.scene[AVALON_PROPERTY] = node = {
                    "name": f"workfile{task_name}"
                }

                created_inst["instance_node"] = node
                data = created_inst.data_to_store()

            imprint(node, data)
