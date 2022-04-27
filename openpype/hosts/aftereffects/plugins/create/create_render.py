from openpype import resources
from openpype.lib import BoolDef, UISeparatorDef
from openpype.hosts.aftereffects import api
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    CreatorError,
    legacy_io,
)


class RenderCreator(Creator):
    identifier = "render"
    label = "Render"
    family = "render"
    description = "Render creator"

    create_allow_context_change = True

    def __init__(
        self, create_context, system_settings, project_settings, headless=False
    ):
        super(RenderCreator, self).__init__(create_context, system_settings,
                                            project_settings, headless)
        self._default_variants = (project_settings["aftereffects"]
                                                  ["create"]
                                                  ["RenderCreator"]
                                                  ["defaults"])

    def get_icon(self):
        return resources.get_openpype_splash_filepath()

    def collect_instances(self):
        for instance_data in api.list_instances():
            # legacy instances have family=='render' or 'renderLocal', use them
            creator_id = (instance_data.get("creator_identifier") or
                          instance_data.get("family", '').replace("Local", ''))
            if creator_id == self.identifier:
                instance_data = self._handle_legacy(instance_data)
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            api.get_stub().imprint(created_inst.get("instance_id"),
                                   created_inst.data_to_store())

    def remove_instances(self, instances):
        for instance in instances:
            api.remove_instance(instance)
            self._remove_instance_from_context(instance)

    def create(self, subset_name, data, pre_create_data):
        stub = api.get_stub()  # only after After Effects is up
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
        if not items:
            raise CreatorError((
                "Nothing to create. Select composition "
                "if 'useSelection' or create at least "
                "one composition."
            ))

        for inst in self.create_context.instances:
            if subset_name == inst.subset_name:
                raise CreatorError("{} already exists".format(
                    inst.subset_name))

        data["members"] = [items[0].id]
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        if "farm" in pre_create_data:
            use_farm = pre_create_data["farm"]
            new_instance.creator_attributes["farm"] = use_farm

        api.get_stub().imprint(new_instance.id,
                               new_instance.data_to_store())
        self._add_instance_to_context(new_instance)

    def get_default_variants(self):
        return self._default_variants

    def get_instance_attr_defs(self):
        return [BoolDef("farm", label="Render on farm")]

    def get_pre_create_attr_defs(self):
        output = [
            BoolDef("use_selection", default=True, label="Use selection"),
            UISeparatorDef(),
            BoolDef("farm", label="Render on farm")
        ]
        return output

    def get_detail_description(self):
        return """Creator for Render instances"""

    def _handle_legacy(self, instance_data):
        """Converts old instances to new format."""
        if not instance_data.get("members"):
            instance_data["members"] = [instance_data.get("uuid")]

        if instance_data.get("uuid"):
            # uuid not needed, replaced with unique instance_id
            api.get_stub().remove_instance(instance_data.get("uuid"))
            instance_data.pop("uuid")

        if not instance_data.get("task"):
            instance_data["task"] = legacy_io.Session.get("AVALON_TASK")

        if not instance_data.get("creator_attributes"):
            is_old_farm = instance_data["family"] != "renderLocal"
            instance_data["creator_attributes"] = {"farm": is_old_farm}
            instance_data["family"] = self.family

        return instance_data
