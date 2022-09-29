import openpype.hosts.nuke.api as api
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
    legacy_io,
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
        self.log.debug("__ instance_data: {}".format(instance_data))

        project_name = legacy_io.Session["AVALON_PROJECT"]
        asset_name = legacy_io.Session["AVALON_ASSET"]
        task_name = legacy_io.Session["AVALON_TASK"]
        host_name = legacy_io.Session["AVALON_APP"]

        asset_doc = get_asset_by_name(project_name, asset_name)
        subset_name = self.get_subset_name(
            self.default_variant, task_name, asset_doc,
            project_name, host_name
        )
        self.log.debug("__ subset_name: {}".format(subset_name))
        instance_data.update({
            "asset": asset_name,
            "task": task_name,
            "variant": self.default_variant
        })
        instance_data.update(self.get_dynamic_data(
            self.default_variant, task_name, asset_doc,
            project_name, host_name
        ))

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

        project_name = legacy_io.Session["AVALON_PROJECT"]
        asset_name = legacy_io.Session["AVALON_ASSET"]
        task_name = legacy_io.Session["AVALON_TASK"]
        host_name = legacy_io.Session["AVALON_APP"]

        self.log.debug("__ existing_instance: {}".format(existing_instance))

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
                project_name, host_name
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
