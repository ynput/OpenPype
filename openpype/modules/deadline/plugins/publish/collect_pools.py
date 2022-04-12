# -*- coding: utf-8 -*-
"""Collect Deadline pools. Choose default one from Settings

"""
import pyblish.api


class CollectDeadlinePools(pyblish.api.InstancePlugin):
    """Collect pools from Deadline, if set on instance use these."""

    order = pyblish.api.CollectorOrder + 0.04
    label = "Deadline Webservice from the Instance"
    families = ["rendering", "render.farm", "renderFarm"]

    primary_pool = None
    secondary_pool = None

    def process(self, instance):

        if not instance.data.get("primaryPool"):
            self.instance.data["primaryPool"] = self.primary_pool

        if not instance.data.get("secondaryPool"):
            self.instance.data["secondaryPool"] = self.secondary_pool
