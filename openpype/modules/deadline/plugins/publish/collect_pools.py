# -*- coding: utf-8 -*-
"""Collect Deadline pools. Choose default one from Settings

"""
import pyblish.api

from openpype.lib import TextDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectDeadlinePools(pyblish.api.InstancePlugin,
                           OpenPypePyblishPluginMixin):
    """Collect pools from instance if present, from Setting otherwise."""

    order = pyblish.api.CollectorOrder + 0.420
    label = "Collect Deadline Pools"
    families = ["rendering", "render.farm", "renderFarm", "renderlayer"]

    primary_pool = None
    secondary_pool = None

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        # deadline.publish.CollectDeadlinePools
        settings = project_settings["deadline"]["publish"]["CollectDeadlinePools"]  # noqa
        cls.primary_pool = settings.get("primary_pool", None)
        cls.secondary_pool = settings.get("secondary_pool", None)

    def process(self, instance):

        settings = self.get_attr_values_from_data(instance.data)

        if not instance.data.get("primaryPool"):
            instance.data["primaryPool"] = (
                settings.get("primaryPool") or self.primary_pool or "none"
            )

        if not instance.data.get("secondaryPool"):
            instance.data["secondaryPool"] = (
                settings.get("secondaryPool") or self.secondary_pool or "none"
            )

    def get_attribute_defs(self):

        # TODO: Preferably this would be an enum for the user
        #       but the Deadline server URL can be dynamic and
        #       can be set per render instance. Since get_attribute_defs
        #       can't be dynamic unfortunately EnumDef isn't possible (yet?)
        # pool_names = self.deadline_module.get_deadline_pools(deadline_url,
        #                                                      self.log)
        # secondary_pool_names = ["-"] + pool_names

        return [
            TextDef("primaryPool",
                    label="Primary Pool",
                    default=self.primary_pool),
            TextDef("secondaryPool",
                    label="Secondary Pool",
                    default=self.secondary_pool)
        ]
