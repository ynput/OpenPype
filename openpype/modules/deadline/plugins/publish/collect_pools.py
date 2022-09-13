# -*- coding: utf-8 -*-
"""Collect Deadline pools. Choose default one from Settings

"""
import pyblish.api


class CollectDeadlinePools(pyblish.api.InstancePlugin):
    """Collect pools from instance if present, from Setting otherwise."""

    order = pyblish.api.CollectorOrder + 0.420
    label = "Collect Deadline Pools"
    families = ["rendering", "render.farm", "renderFarm", "renderlayer"]

    primary_pool = None
    secondary_pool = None

    def process(self, instance):
        if not instance.data.get("primaryPool"):
            instance.data["primaryPool"] = self.primary_pool or "none"

        if not instance.data.get("secondaryPool"):
            instance.data["secondaryPool"] = self.secondary_pool or "none"
