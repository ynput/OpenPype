import json
from openpype import resources
import openpype.hosts.aftereffects.api as api
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    lib,
    CreatorError
)


class RenderCreator(Creator):
    identifier = "render"
    label = "Render"
    family = "render"
    description = "Render creator"

    create_allow_context_change = False

    def get_icon(self):
        return resources.get_openpype_splash_filepath()

    def collect_instances(self):
        for instance_data in api.list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance_data = self._handle_legacy(instance_data)
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        created_inst, changes = update_list[0]
        print("RenderCreator update_list:: {}-{}".format(created_inst, changes))
        api.get_stub().imprint(created_inst.get("instance_id"),
                               created_inst.data_to_store())

    def remove_instances(self, instances):
        for instance in instances:
            print("instance:: {}".format(instance))
            api.remove_instance(instance)
            self._remove_instance_from_context(instance)

    def create(self, subset_name, data, pre_create_data):
        print("Data that can be used in create:\n{}".format(
            json.dumps(pre_create_data, indent=4)
        ))
        stub = api.get_stub()  # only after After Effects is up
        print("pre_create_data:: {}".format(pre_create_data))
        if pre_create_data.get("use_selection"):
            items = stub.get_selected_items(
                comps=True, folders=False, footages=False
            )
        else:
            items = stub.get_items(comps=True, folders=False, footages=False)

        if len(items) > 1:
            raise CreatorError(
                "Please select only single composition at time."
            )
        print("items:: {}".format(items))
        if not items:
            raise CreatorError((
                "Nothing to create. Select composition "
                "if 'useSelection' or create at least "
                "one composition."
            ))

        data["members"] = [items[0].id]
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        new_instance.creator_attributes["farm"] = pre_create_data["farm"]

        api.get_stub().imprint(new_instance.get("instance_id"),
                               new_instance.data_to_store())
        self.log.info(new_instance.data)
        self._add_instance_to_context(new_instance)

    def get_default_variants(self):
        return [
            "myVariant",
            "variantTwo",
            "different_variant"
        ]

    def get_instance_attr_defs(self):
        return [lib.BoolDef("farm", label="Render on farm")]

    def get_pre_create_attr_defs(self):
        output = [
            lib.BoolDef("use_selection", default=True, label="Use selection"),
            lib.UISeparatorDef(),
            lib.BoolDef("farm", label="Render on farm")
        ]
        return output

    def get_detail_description(self):
        return """Creator for Render instances"""

    def _handle_legacy(self, instance_data):
        """Converts old instances to new format."""
        if instance_data.get("uuid"):
            instance_data["item_id"] = instance_data.get("uuid")
            instance_data.pop("uuid")

        if not instance_data.get("members"):
            instance_data["members"] = [instance_data["item_id"]]

        return instance_data

