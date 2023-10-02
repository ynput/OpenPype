import re

from openpype.hosts.photoshop import api
from openpype.lib import BoolDef
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    CreatorError
)
from openpype.lib import prepare_template_data
from openpype.pipeline.create import SUBSET_NAME_ALLOWED_SYMBOLS
from openpype.hosts.photoshop.api.pipeline import cache_and_get_instances
from openpype.hosts.photoshop.lib import clean_subset_name


class ImageCreator(Creator):
    """Creates image instance for publishing.

    Result of 'image' instance is image of all visible layers, or image(s) of
    selected layers.
    """
    identifier = "image"
    label = "Image"
    family = "image"
    description = "Image creator"

    # Settings
    default_variants = ""
    mark_for_review = False
    active_on_create = True

    def create(self, subset_name_from_ui, data, pre_create_data):
        groups_to_create = []
        top_layers_to_wrap = []
        create_empty_group = False

        stub = api.stub()  # only after PS is up
        top_level_selected_items = stub.get_selected_layers()
        if pre_create_data.get("use_selection"):
            only_single_item_selected = len(top_level_selected_items) == 1
            if (
                    only_single_item_selected or
                    pre_create_data.get("create_multiple")):
                for selected_item in top_level_selected_items:
                    if selected_item.group:
                        groups_to_create.append(selected_item)
                    else:
                        top_layers_to_wrap.append(selected_item)
            else:
                group = stub.group_selected_layers(subset_name_from_ui)
                groups_to_create.append(group)
        else:
            stub.select_layers(stub.get_layers())
            try:
                group = stub.group_selected_layers(subset_name_from_ui)
            except:
                raise CreatorError("Cannot group locked Background layer!")
            groups_to_create.append(group)

        # create empty group if nothing selected
        if not groups_to_create and not top_layers_to_wrap:
            group = stub.create_group(subset_name_from_ui)
            groups_to_create.append(group)

        # wrap each top level layer into separate new group
        for layer in top_layers_to_wrap:
            stub.select_layers([layer])
            group = stub.group_selected_layers(layer.name)
            groups_to_create.append(group)

        layer_name = ''
        # use artist chosen option OR force layer if more subsets are created
        # to differentiate them
        use_layer_name = (pre_create_data.get("use_layer_name") or
                          len(groups_to_create) > 1)
        for group in groups_to_create:
            subset_name = subset_name_from_ui  # reset to name from creator UI
            layer_names_in_hierarchy = []
            created_group_name = self._clean_highlights(stub, group.name)

            if use_layer_name:
                layer_name = re.sub(
                    "[^{}]+".format(SUBSET_NAME_ALLOWED_SYMBOLS),
                    "",
                    group.name
                )
                if "{layer}" not in subset_name.lower():
                    subset_name += "{Layer}"

            layer_fill = prepare_template_data({"layer": layer_name})
            subset_name = subset_name.format(**layer_fill)
            subset_name = clean_subset_name(subset_name)

            if group.long_name:
                for directory in group.long_name[::-1]:
                    name = self._clean_highlights(stub, directory)
                    layer_names_in_hierarchy.append(name)

            data_update = {
                "subset": subset_name,
                "members": [str(group.id)],
                "layer_name": layer_name,
                "long_name": "_".join(layer_names_in_hierarchy)
            }
            data.update(data_update)

            mark_for_review = (pre_create_data.get("mark_for_review") or
                               self.mark_for_review)
            creator_attributes = {"mark_for_review": mark_for_review}
            data.update({"creator_attributes": creator_attributes})

            if not self.active_on_create:
                data["active"] = False

            new_instance = CreatedInstance(self.family, subset_name, data,
                                           self)

            stub.imprint(new_instance.get("instance_id"),
                         new_instance.data_to_store())
            self._add_instance_to_context(new_instance)
            # reusing existing group, need to rename afterwards
            if not create_empty_group:
                stub.rename_layer(group.id,
                                  stub.PUBLISH_ICON + created_group_name)

    def collect_instances(self):
        for instance_data in cache_and_get_instances(self):
            # legacy instances have family=='image'
            creator_id = (instance_data.get("creator_identifier") or
                          instance_data.get("family"))

            if creator_id == self.identifier:
                instance_data = self._handle_legacy(instance_data)
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

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
            self.host.remove_instance(instance)
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        output = [
            BoolDef("use_selection", default=True,
                    label="Create only for selected"),
            BoolDef("create_multiple",
                    default=True,
                    label="Create separate instance for each selected"),
            BoolDef("use_layer_name",
                    default=False,
                    label="Use layer name in subset"),
            BoolDef(
                "mark_for_review",
                label="Create separate review",
                default=False
            )
        ]
        return output

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "mark_for_review",
                label="Review"
            )
        ]

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["photoshop"]["create"]["ImageCreator"]
        )

        self.active_on_create = plugin_settings["active_on_create"]
        self.default_variants = plugin_settings["default_variants"]
        self.mark_for_review = plugin_settings["mark_for_review"]
        self.enabled = plugin_settings["enabled"]

    def get_detail_description(self):
        return """Creator for Image instances

        Main publishable item in Photoshop will be of `image` family. Result of
        this item (instance) is picture that could be loaded and used
        in another DCCs (for example as single layer in composition in
        AfterEffects, reference in Maya etc).

        There are couple of options what to publish:
        - separate image per selected layer (or group of layers)
        - one image for all selected layers
        - all visible layers (groups) flattened into single image

        In most cases you would like to keep `Create only for selected`
        toggled on and select what you would like to publish.
        Toggling this option off will allow you to create instance for all
        visible layers without a need to select them explicitly.

        Use 'Create separate instance for each selected' to create separate
        images per selected layer (group of layers).

        'Use layer name in subset' will explicitly add layer name into subset
        name. Position of this name is configurable in
        `project_settings/global/tools/creator/subset_name_profiles`.
        If layer placeholder ({layer}) is not used in `subset_name_profiles`
        but layer name should be used (set explicitly in UI or implicitly if
        multiple images should be created), it is added in capitalized form
        as a suffix to subset name.

        Each image could have its separate review created if necessary via
        `Create separate review` toggle.
        But more use case is to use separate `review` instance to create review
        from all published items.
        """

    def _handle_legacy(self, instance_data):
        """Converts old instances to new format."""
        if not instance_data.get("members"):
            instance_data["members"] = [instance_data.get("uuid")]

        if instance_data.get("uuid"):
            # uuid not needed, replaced with unique instance_id
            api.stub().remove_instance(instance_data.get("uuid"))
            instance_data.pop("uuid")

        if not instance_data.get("task"):
            instance_data["task"] = self.create_context.get_current_task_name()

        if not instance_data.get("variant"):
            instance_data["variant"] = ''

        return instance_data

    def _clean_highlights(self, stub, item):
        return item.replace(stub.PUBLISH_ICON, '').replace(stub.LOADED_ICON,
                                                           '')

    def get_dynamic_data(self, variant, task_name, asset_doc,
                         project_name, host_name, instance):
        if instance is not None:
            layer_name = instance.get("layer_name")
            if layer_name:
                return {"layer": layer_name}
        return {"layer": "{layer}"}
