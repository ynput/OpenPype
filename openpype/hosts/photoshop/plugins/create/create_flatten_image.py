from openpype.pipeline import CreatedInstance, CreatorError

from openpype.lib import (
    prepare_template_data,
    TextDef,
    BoolDef,
)

import openpype.hosts.photoshop.api as api
from openpype.hosts.photoshop.lib import PSAutoCreator


class AutoImageCreator(PSAutoCreator):
    """Creates flatten image from all visible layers.

    Used in simplified publishing as auto created instance.
    Must be enabled in Setting and template for subset name provided
    """
    identifier = "auto_image"
    family = "image"

    # Settings
    # - template for subset name
    flatten_subset_template = ""
    # - Mark by default instance for review
    mark_for_review = True

    def create(self, options=None):
        existing_instance = None
        for instance in self.create_context.instances:
            if instance.creator_identifier == self.identifier:
                existing_instance = instance
                break

        context = self.create_context
        asset_name = context.get_current_asset_name()
        task_name = context.get_current_task_name()
        if existing_instance is None:
            subset_name = self._get_subset_name(asset_name, task_name)

            asset_name = context.get_current_asset_name()
            task_name = context.get_current_task_name()

            publishable_ids = [layer.id for layer in api.stub().get_layers()
                               if layer.visible]
            data = {
                "asset": asset_name,
                "task": task_name,
                "members": publishable_ids
            }

            creator_attributes = {"mark_for_review": self.mark_for_review}
            data.update({"creator_attributes": creator_attributes})

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            self._add_instance_to_context(new_instance)
            api.stub().imprint(new_instance.get("instance_id"),
                               new_instance.data_to_store())

        elif (  # existing instance from different context
            existing_instance["asset"] != asset_name
            or existing_instance["task"] != task_name
        ):
            subset_name = self._get_subset_name(asset_name, task_name)

            existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name

            api.stub().imprint(existing_instance.get("instance_id"),
                               existing_instance.data_to_store())


    def _get_subset_name(self, asset_name, task_name):
        """Use configured template to create subset name"""
        if not self.flatten_subset_template:
            raise CreatorError((
                "You need to provide template for subset name in Settings."
            ))

        fill_pairs = {
            "asset": asset_name,
            "task": task_name
        }

        subset_name = self.flatten_subset_template.format(
            **prepare_template_data(fill_pairs))
        return subset_name

    def get_pre_create_attr_defs(self):
        return [
            TextDef(
                "flatten_subset_template",
                label="Subset name template",
                items=TextDef
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "mark_for_review",
                label="Review"
            )
        ]

    def apply_settings(self, project_settings, system_settings):
        plugin_settings = (
            project_settings["photoshop"]["create"]["AutoImageCreator"]
        )

        self.flatten_subset_template = \
            plugin_settings["flatten_subset_template"]
        self.mark_for_review = plugin_settings["mark_for_review"]
        self.enabled = plugin_settings["enabled"]

    def get_detail_description(self):
        return """Creator for flatten image.

        Studio might configure simple publishing workflow. In that case
        `image` instance is automatically created which will publish flat
        image from all visible layers.

        Artist might disable this instance from publishing or from creating
        review for it though.
        """
