# -*- coding: utf-8 -*-
"""Creator plugin for model."""
from openpype.hosts.max.api import plugin
from openpype.lib import BoolDef


class CreateModel(plugin.MaxCreator):
    """Creator plugin for Model."""
    identifier = "io.openpype.creators.max.model"
    label = "Model"
    family = "model"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data["custom_attrs"] = pre_create_data.get(
            "custom_attrs")

        super(CreateModel, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_pre_create_attr_defs(self):
        attrs = super().get_pre_create_attr_defs()
        return attrs + [
            BoolDef("custom_attrs",
                    label="Custom Attributes",
                    default=False),
        ]
