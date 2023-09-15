# -*- coding: utf-8 -*-
"""Creator plugin for creating TyCache."""
from openpype.hosts.max.api import plugin
from openpype.lib import EnumDef


class CreateTyCache(plugin.MaxCreator):
    """Creator plugin for TyCache."""
    identifier = "io.openpype.creators.max.tycache"
    label = "TyCache"
    family = "tycache"
    icon = "gear"

    def create(self, subset_name, instance_data, pre_create_data):
        instance_data["tycache_type"] = pre_create_data.get(
            "tycache_type")
        super(CreateTyCache, self).create(
            subset_name,
            instance_data,
            pre_create_data)

    def get_pre_create_attr_defs(self):
        attrs = super(CreateTyCache, self).get_pre_create_attr_defs()

        tycache_format_enum = ["tycache", "tycachespline"]

        return attrs + [

            EnumDef("tycache_type",
                    tycache_format_enum,
                    default="tycache",
                    label="TyCache Type")
        ]
