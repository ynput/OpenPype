"""Base plugin class for 3DEqualizer.

note:
    3dequalizer 7.1v2 uses Python 3.7.9

"""
from abc import ABC
from typing import Dict, List

from openpype.hosts.equalizer.api import EqualizerHost
from openpype.lib import BoolDef, EnumDef, NumberDef
from openpype.pipeline import (
    CreatedInstance,
    Creator,
    OptionalPyblishPluginMixin,
)


class EqualizerCreator(ABC, Creator):

    @property
    def host(self) -> EqualizerHost:
        """Return the host application."""
        # We need to cast the host to EqualizerHost, because the Creator
        # class is not aware of the host application.
        return super().host

    def create(self, subset_name, instance_data, pre_create_data):
        """Create a subset in the host application.

        Args:
            subset_name (str): Name of the subset to create.
            instance_data (dict): Data of the instance to create.
            pre_create_data (dict): Data from the pre-create step.

        Returns:
            openpype.pipeline.CreatedInstance: Created instance.
        """
        self.log.debug("EqualizerCreator.create")
        instance = CreatedInstance(
            self.family,
            subset_name,
            instance_data,
            self)
        self._add_instance_to_context(instance)
        return instance

    def collect_instances(self):
        """Collect instances from the host application.

        Returns:
            list[openpype.pipeline.CreatedInstance]: List of instances.
        """
        for instance_data in self.host.get_context_data().get(
                "publish_instances", []):
            created_instance = CreatedInstance.from_existing(
                instance_data, self
            )
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):

        # if not update_list:
        #     return
        context = self.host.get_context_data()
        if not context.get("publish_instances"):
            context["publish_instances"] = []

        instances_by_id = {}
        for instance in context.get("publish_instances"):
            # sourcery skip: use-named-expression
            instance_id = instance.get("instance_id")
            if instance_id:
                instances_by_id[instance_id] = instance

        for instance, changes in update_list:
            new_instance_data = changes.new_value
            instance_data = instances_by_id.get(instance.id)
            # instance doesn't exist, append everything
            if instance_data is None:
                context["publish_instances"].append(new_instance_data)
                continue

            # update only changed values on instance
            for key in set(instance_data) - set(new_instance_data):
                instance_data.pop(key)
                instance_data.update(new_instance_data)

        self.host.update_context_data(context, changes=update_list)

    def remove_instances(self, instances: List[Dict]):
        context = self.host.get_context_data()
        if not context.get("publish_instances"):
            context["publish_instances"] = []

        ids_to_remove = [
            instance.get("instance_id")
            for instance in instances
        ]
        for instance in context.get("publish_instances"):
            if instance.get("instance_id") in ids_to_remove:
                context["publish_instances"].remove(instance)

        self.host.update_context_data(context, changes={})


class ExtractScriptBase(OptionalPyblishPluginMixin):
    """Base class for extract script plugins."""

    hide_reference_frame = False
    export_uv_textures = False
    overscan_percent_width = 100
    overscan_percent_height = 100
    units = "mm"

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        settings = project_settings["equalizer"]["publish"][
            "ExtractMatchmoveScriptMaya"]  # noqa

        cls.hide_reference_frame = settings.get(
            "hide_reference_frame", cls.hide_reference_frame)
        cls.export_uv_textures = settings.get(
            "export_uv_textures", cls.export_uv_textures)
        cls.overscan_percent_width = settings.get(
            "overscan_percent_width", cls.overscan_percent_width)
        cls.overscan_percent_height = settings.get(
            "overscan_percent_height", cls.overscan_percent_height)
        cls.units = settings.get("units", cls.units)

    @classmethod
    def get_attribute_defs(cls):
        defs = super(ExtractScriptBase, cls).get_attribute_defs()

        defs.extend([
            BoolDef("hide_reference_frame",
                    label="Hide Reference Frame",
                    default=cls.hide_reference_frame),
            BoolDef("export_uv_textures",
                    label="Export UV Textures",
                    default=cls.export_uv_textures),
            NumberDef("overscan_percent_width",
                      label="Overscan Width %",
                      default=cls.overscan_percent_width,
                      decimals=0,
                      minimum=1,
                      maximum=1000),
            NumberDef("overscan_percent_height",
                      label="Overscan Height %",
                      default=cls.overscan_percent_height,
                      decimals=0,
                      minimum=1,
                      maximum=1000),
            EnumDef("units",
                    ["mm", "cm", "m", "in", "ft", "yd"],
                    default=cls.units,
                    label="Units"),
        ])
        return defs
