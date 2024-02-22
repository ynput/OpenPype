# -*- coding: utf-8 -*-
"""Collect Deadline pools. Choose default one from Settings

"""
import pyblish.api
from openpype.lib import EnumDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin
from openpype.modules.deadline.utils import DeadlineDefaultJobAttrs
from openpype.pipeline.context_tools import _get_modules_manager


class CollectDeadlinePools(pyblish.api.InstancePlugin,
                           OpenPypePyblishPluginMixin,
                           DeadlineDefaultJobAttrs):
    """Collect pools from instance if present, from Setting otherwise."""

    order = pyblish.api.CollectorOrder + 0.420
    label = "Collect Deadline Pools"
    families = ["rendering",
                "render.farm",
                "render.frames_farm",
                "renderFarm",
                "renderlayer",
                "maxrender"]

    def process(self, instance):
        attr_values = self.get_attr_values_from_data(instance.data)

        if not instance.data.get("pool"):
            instance.data["pool"] = attr_values.get("pool", self.pool)
        elif instance.data["pool"] == "-":
            instance.data["pool"] = ""

        if not instance.data.get("pool_secondary"):
            instance.data["pool_secondary"] = attr_values.get("pool_secondary", self.pool_secondary)
        elif instance.data["pool_secondary"] == "-":
            instance.data["pool_secondary"] = ""
