# -*- coding: utf-8 -*-
"""Creator plugin for creating pointcache alembics."""
from openpype.hosts.max.api import plugin
from openpype.lib import BoolDef


class CreatePointCache(plugin.MaxCreator):
    """Creator plugin for Point caches."""
    identifier = "io.openpype.creators.max.pointcache"
    label = "Point Cache"
    family = "pointcache"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data["custom_attrs"] = pre_create_data.get(
            "custom_attrs")

        super(CreatePointCache, self).create(
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
