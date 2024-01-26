# -*- coding: utf-8 -*-
"""Collect Deadline pools. Choose default one from Settings

"""
import pyblish.api
from openpype.lib import (
    TextDef,
    filter_profiles
)
from openpype.pipeline.publish import OpenPypePyblishPluginMixin
from openpype.pipeline.context_tools import get_current_task_name


class CollectDeadlinePools(pyblish.api.InstancePlugin,
                           OpenPypePyblishPluginMixin):
    """Collect pools from instance if present, from Setting otherwise."""

    order = pyblish.api.CollectorOrder + 0.420
    label = "Collect Deadline Pools"
    families = ["rendering",
                "render.farm",
                "render.frames_farm",
                "renderFarm",
                "renderlayer",
                "maxrender"]

    primary_pool = None
    secondary_pool = None

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        # deadline.publish.CollectDeadlinePools
        profile = cls.get_profile(self=cls, project_settings=project_settings)
        if profile:
            cls.primary_pool = profile.get("primary_pool", cls.primary_pool)
            cls.secondary_pool = profile.get(
                "secondary_pool",
                cls.secondary_pool
            )

    def get_profile(self, project_settings):
        settings = project_settings["deadline"]["DefaultJobSettings"] # noqa
        task = get_current_task_name()
        profile = None

        filtering_criteria = {
            "hosts": "maya",
            "task_types": task
        }
        if settings.get("profiles"):
            profile = filter_profiles(
                settings["profiles"],
                filtering_criteria,
                logger=self.log
            )

        return profile

    def process(self, instance):

        attr_values = self.get_attr_values_from_data(instance.data)
        if not instance.data.get("primaryPool"):
            instance.data["primaryPool"] = (
                attr_values.get("primaryPool") or self.primary_pool or "none"
            )
        if instance.data["primaryPool"] == "-":
            instance.data["primaryPool"] = None

        if not instance.data.get("secondaryPool"):
            instance.data["secondaryPool"] = (
                attr_values.get("secondaryPool") or self.secondary_pool or "none"  # noqa
            )

        if instance.data["secondaryPool"] == "-":
            instance.data["secondaryPool"] = None

    @classmethod
    def get_attribute_defs(cls):
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
                    default=cls.primary_pool),
            TextDef("secondaryPool",
                    label="Secondary Pool",
                    default=cls.secondary_pool)
        ]
