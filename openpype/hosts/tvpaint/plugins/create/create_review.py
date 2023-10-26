from openpype import AYON_SERVER_ENABLED
from openpype.client import get_asset_by_name
from openpype.pipeline import CreatedInstance
from openpype.hosts.tvpaint.api.plugin import TVPaintAutoCreator


class TVPaintReviewCreator(TVPaintAutoCreator):
    family = "review"
    identifier = "scene.review"
    label = "Review"
    icon = "ei.video"

    # Settings
    active_on_create = True

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["tvpaint"]["create"]["create_review"]
        )
        self.default_variant = plugin_settings["default_variant"]
        self.default_variants = plugin_settings["default_variants"]
        self.active_on_create = plugin_settings["active_on_create"]

    def create(self):
        existing_instance = None
        for instance in self.create_context.instances:
            if instance.creator_identifier == self.identifier:
                existing_instance = instance
                break

        create_context = self.create_context
        host_name = create_context.host_name
        project_name = create_context.get_current_project_name()
        asset_name = create_context.get_current_asset_name()
        task_name = create_context.get_current_task_name()

        if existing_instance is None:
            existing_asset_name = None
        elif AYON_SERVER_ENABLED:
            existing_asset_name = existing_instance["folderPath"]
        else:
            existing_asset_name = existing_instance["asset"]

        if existing_instance is None:
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                self.default_variant,
                task_name,
                asset_doc,
                project_name,
                host_name
            )
            data = {
                "task": task_name,
                "variant": self.default_variant
            }
            if AYON_SERVER_ENABLED:
                data["folderPath"] = asset_name
            else:
                data["asset"] = asset_name

            if not self.active_on_create:
                data["active"] = False

            new_instance = CreatedInstance(
                self.family, subset_name, data, self
            )
            instances_data = self.host.list_instances()
            instances_data.append(new_instance.data_to_store())
            self.host.write_instances(instances_data)
            self._add_instance_to_context(new_instance)

        elif (
            existing_asset_name != asset_name
            or existing_instance["task"] != task_name
        ):
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                existing_instance["variant"],
                task_name,
                asset_doc,
                project_name,
                host_name,
                existing_instance
            )
            if AYON_SERVER_ENABLED:
                existing_instance["folderPath"] = asset_name
            else:
                existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name
