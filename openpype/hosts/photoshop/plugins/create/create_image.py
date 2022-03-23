from avalon import api as avalon_api
from openpype.hosts.photoshop import api
from openpype.lib import BoolDef
from openpype.pipeline import (
    Creator,
    CreatedInstance
)


class ImageCreator(Creator):
    """Creates image instance for publishing."""
    identifier = "image"
    label = "Image"
    family = "image"
    description = "Image creator"

    def collect_instances(self):
        for instance_data in api.list_instances():
            # legacy instances have family=='image'
            creator_id = (instance_data.get("creator_identifier") or
                          instance_data.get("family"))

            if creator_id == self.identifier:
                instance_data = self._handle_legacy(instance_data)
                layer = api.stub().get_layer(instance_data["members"][0])
                instance_data["layer"] = layer
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def create(self, subset_name_from_ui, data, pre_create_data):
        groups_to_create = []
        top_layers_to_wrap = []
        create_empty_group = False

        stub = api.stub()  # only after PS is up
        top_level_selected_items = stub.get_selected_layers()
        if pre_create_data.get("use_selection"):
            only_single_item_selected = len(top_level_selected_items) == 1
            for selected_item in top_level_selected_items:
                if (
                        only_single_item_selected or
                        pre_create_data.get("create_multiple")):
                    if selected_item.group:
                        groups_to_create.append(selected_item)
                    else:
                        top_layers_to_wrap.append(selected_item)
                else:
                    group = stub.group_selected_layers(subset_name_from_ui)
                    groups_to_create.append(group)

        if not groups_to_create and not top_layers_to_wrap:
            group = stub.create_group(subset_name_from_ui)
            groups_to_create.append(group)

        # wrap each top level layer into separate new group
        for layer in top_layers_to_wrap:
            stub.select_layers([layer])
            group = stub.group_selected_layers(layer.name)
            groups_to_create.append(group)

        creating_multiple_groups = len(groups_to_create) > 1
        for group in groups_to_create:
            subset_name = subset_name_from_ui  # reset to name from creator UI
            layer_names_in_hierarchy = []
            created_group_name = self._clean_highlights(stub, group.name)

            if creating_multiple_groups:
                # concatenate with layer name to differentiate subsets
                subset_name += group.name.title().replace(" ", "")

            if group.long_name:
                for directory in group.long_name[::-1]:
                    name = self._clean_highlights(stub, directory)
                    layer_names_in_hierarchy.append(name)

            data.update({"subset": subset_name})
            data.update({"members": [str(group.id)]})
            data.update({"long_name": "_".join(layer_names_in_hierarchy)})

            new_instance = CreatedInstance(self.family, subset_name, data,
                                           self)

            stub.imprint(new_instance.get("instance_id"),
                         new_instance.data_to_store())
            self._add_instance_to_context(new_instance)
            # reusing existing group, need to rename afterwards
            if not create_empty_group:
                stub.rename_layer(group.id,
                                  stub.PUBLISH_ICON + created_group_name)

    def update_instances(self, update_list):
        self.log.debug("update_list:: {}".format(update_list))
        for created_inst, _changes in update_list:
            if created_inst.get("layer"):
                # not storing PSItem layer to metadata
                created_inst.pop("layer")
            api.stub().imprint(created_inst.get("instance_id"),
                               created_inst.data_to_store())

    def remove_instances(self, instances):
        for instance in instances:
            api.remove_instance(instance)
            self._remove_instance_from_context(instance)

    def get_default_variants(self):
        return [
            "Main"
        ]

    def get_pre_create_attr_defs(self):
        output = [
            BoolDef("use_selection", default=True,
                    label="Create only for selected"),
            BoolDef("create_multiple",
                    default=True,
                    label="Create separate instance for each selected")
        ]
        return output

    def get_detail_description(self):
        return """Creator for Image instances"""

    def _handle_legacy(self, instance_data):
        """Converts old instances to new format."""
        if not instance_data.get("members"):
            instance_data["members"] = [instance_data.get("uuid")]

        if instance_data.get("uuid"):
            # uuid not needed, replaced with unique instance_id
            api.stub().remove_instance(instance_data.get("uuid"))
            instance_data.pop("uuid")

        if not instance_data.get("task"):
            instance_data["task"] = avalon_api.Session.get("AVALON_TASK")

        if not instance_data.get("variant"):
            instance_data["variant"] = ''

        return instance_data

    def _clean_highlights(self, stub, item):
        return item.replace(stub.PUBLISH_ICON, '').replace(stub.LOADED_ICON,
                                                           '')
