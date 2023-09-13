import openpype.hosts.nuke.api as api
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
)
from openpype.hosts.nuke.api import (
    INSTANCE_DATA_KNOB,
    set_node_data
)
import nuke


class WorkfileCreator(AutoCreator):
    identifier = "workfile"
    family = "workfile"

    default_variant = "Main"

    def get_instance_attr_defs(self):
        return []

    def collect_instances(self):
        root_node = nuke.root()
        instance_data = api.get_node_data(
            root_node, api.INSTANCE_DATA_KNOB
        )

        project_name = self.create_context.get_current_project_name()
        asset_name = self.create_context.get_current_asset_name()
        task_name = self.create_context.get_current_task_name()
        host_name = self.create_context.host_name

        asset_doc = get_asset_by_name(project_name, asset_name)
        subset_name = self.get_subset_name(
            self.default_variant, task_name, asset_doc,
            project_name, host_name
        )
        instance_data.update({
            "asset": asset_name,
            "task": task_name,
            "variant": self.default_variant
        })
        instance_data.update(self.get_dynamic_data(
            self.default_variant, task_name, asset_doc,
            project_name, host_name, instance_data
        ))

        instance = CreatedInstance(
            self.family, subset_name, instance_data, self
        )
        instance.transient_data["node"] = root_node
        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            instance_node = created_inst.transient_data["node"]

            set_node_data(
                instance_node,
                INSTANCE_DATA_KNOB,
                created_inst.data_to_store()
            )

    def create(self, options=None):
        # no need to create if it is created
        # in `collect_instances`
        pass
