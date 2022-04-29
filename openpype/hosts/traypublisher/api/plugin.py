from openpype.pipeline import (
    Creator,
    CreatedInstance
)
from openpype.lib import (
    FileDef,
    BoolDef,
)

from .pipeline import (
    list_instances,
    update_instances,
    remove_instances,
    HostContext,
)


class TrayPublishCreator(Creator):
    create_allow_context_change = True

    def collect_instances(self):
        for instance_data in list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        update_instances(update_list)

    def remove_instances(self, instances):
        remove_instances(instances)
        for instance in instances:
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attrobites
        return self.get_instance_attr_defs()


class SettingsCreator(TrayPublishCreator):
    create_allow_context_change = True

    enable_review = False
    extensions = []

    def collect_instances(self):
        for instance_data in list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def create(self, subset_name, data, pre_create_data):
        # Pass precreate data to creator attributes
        data["creator_attributes"] = pre_create_data
        data["settings_creator"] = True
        # Create new instance
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        # Host implementation of storing metadata about instance
        HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)

    def get_instance_attr_defs(self):
        output = []

        file_def = FileDef(
            "filepath",
            folders=False,
            extensions=self.extensions,
            allow_sequences=self.allow_sequences,
            label="Filepath",
        )
        output.append(file_def)
        if self.enable_review:
            output.append(BoolDef("review", label="Review"))
        return output

    @classmethod
    def from_settings(cls, item_data):
        identifier = item_data["identifier"]
        family = item_data["family"]
        if not identifier:
            identifier = "settings_{}".format(family)
        return type(
            "{}{}".format(cls.__name__, identifier),
            (cls, ),
            {
                "family": family,
                "identifier": identifier,
                "label": item_data["label"].strip(),
                "icon": item_data["icon"],
                "description": item_data["description"],
                "detailed_description": item_data["detailed_description"],
                "enable_review": item_data["enable_review"],
                "extensions": item_data["extensions"],
                "allow_sequences": item_data["allow_sequences"],
                "default_variants": item_data["default_variants"]
            }
        )
