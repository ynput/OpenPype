from openpype import AYON_SERVER_ENABLED
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
)
from openpype.hosts.gaffer.api import (
    get_root,
)
from openpype.hosts.gaffer.api.plugin import CreatorImprintReadMixin


class GafferWorkfileCreator(AutoCreator, CreatorImprintReadMixin):
    identifier = "io.openpype.creators.gaffer.workfile"
    family = "workfile"
    label = "Workfile"
    icon = "fa5.file"

    default_variant = "Main"

    create_allow_context_change = False

    attr_prefix = "openpype_workfile_"

    def collect_instances(self):

        script = get_root()
        if not script:
            return

        data = self._read(script)
        if not data or data.get("creator_identifier") != self.identifier:
            return

        instance = CreatedInstance(
            family=self.family,
            subset_name=data["subset"],
            data=data,
            creator=self
        )
        instance.transient_data["node"] = script

        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            node = created_inst.transient_data["node"]

            # Imprint data into the script root
            data = created_inst.data_to_store()
            self._imprint(node, data)

    def create(self, options=None):

        script = get_root()
        if not script:
            self.log.error("Unable to find current script")
            return

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

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            new_instance.transient_data["node"] = script
            self._add_instance_to_context(new_instance)

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
