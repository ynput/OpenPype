from avalon import api as avalon_api
from openpype.hosts.photoshop import api
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    lib,
    CreatorError
)


class ImageCreator(Creator):
    """Creates image instance for publishing."""
    identifier = "image"
    label = "Image"
    family = "image"
    description = "Image creator"

    def collect_instances(self):
        import json
        self.log.info("ImageCreator: api.list_instances():: {}".format(
            json.dumps(api.list_instances(), indent=4)))
        for instance_data in api.list_instances():
            # legacy instances have family=='image'
            creator_id = (instance_data.get("creator_identifier") or
                          instance_data.get("family"))

            self.log.info("ImageCreator: instance_data:: {}".format(json.dumps(instance_data, indent=4)))
            if creator_id == self.identifier:
                instance_data = self._handle_legacy(instance_data)

                layer = api.stub().get_layer(instance_data["members"][0])
                instance_data["layer"] = layer
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def create(self, subset_name, data, pre_create_data):
        groups = []
        layers = []
        create_group = False

        stub = api.stub()  # only after PS is up
        multiple_instances = pre_create_data.get("create_multiple")
        selection = stub.get_selected_layers()
        if pre_create_data.get("use_selection"):
            if len(selection) > 1:
                if multiple_instances:
                    for item in selection:
                        if item.group:
                            groups.append(item)
                        else:
                            layers.append(item)
                else:
                    group = stub.group_selected_layers(subset_name)
                    groups.append(group)
            elif len(selection) == 1:
                # One selected item. Use group if its a LayerSet (group), else
                # create a new group.
                selected_item = selection[0]
                if selected_item.group:
                    groups.append(selected_item)
                else:
                    layers.append(selected_item)
            elif len(selection) == 0:
                # No selection creates an empty group.
                create_group = True
        else:
            group = stub.create_group(subset_name)
            groups.append(group)

        if create_group:
            group = stub.create_group(subset_name)
            groups.append(group)

        for layer in layers:
            stub.select_layers([layer])
            group = stub.group_selected_layers(layer.name)
            groups.append(group)

        for group in groups:
            long_names = []
            group.name = self._clean_highlights(stub, group.name)

            if len(groups) > 1:
                subset_name += group.name.title().replace(" ", "")

            if group.long_name:
                for directory in group.long_name[::-1]:
                    name = self._clean_highlights(stub, directory)
                    long_names.append(name)

            data.update({"subset": subset_name})
            data.update({"layer": group})
            data.update({"members": [str(group.id)]})
            data.update({"long_name": "_".join(long_names)})

            new_instance = CreatedInstance(self.family, subset_name, data,
                                           self)

            stub.imprint(new_instance.get("instance_id"),
                         new_instance.data_to_store())
            self._add_instance_to_context(new_instance)
            # reusing existing group, need to rename afterwards
            if not create_group:
                stub.rename_layer(group.id, stub.PUBLISH_ICON + group.name)

    def update_instances(self, update_list):
        self.log.info("update_list:: {}".format(update_list))
        created_inst, changes = update_list[0]
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
            lib.BoolDef("use_selection", default=True, label="Use selection"),
            lib.BoolDef("create_multiple",
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

        return instance_data

    def _clean_highlights(self, stub, item):
        return item.replace(stub.PUBLISH_ICON, '').replace(stub.LOADED_ICON,
                                                           '')


