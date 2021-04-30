# -*- coding: utf-8 -*-
"""Collect Vray Proxy."""
import pyblish.api


class CollectVrayProxy(pyblish.api.InstancePlugin):
    """Collect Vray Proxy instance.

    Add `pointcache` family for it.
    """
    order = pyblish.api.CollectorOrder + 0.01
    label = 'Collect Vray Proxy'
    families = ["vrayproxy"]

    def process(self, instance):
        """Collector entry point."""
        if not instance.data.get('families'):
            instance.data["families"] = []
        if "pointcache" not in instance.data["families"]:
            instance.data["families"].append("pointcache")
            self.log.debug("adding to pointcache family")
