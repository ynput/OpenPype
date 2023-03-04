# -*- coding: utf-8 -*-
"""Collect Vray Proxy."""
import pyblish.api


class CollectVrayProxy(pyblish.api.InstancePlugin):
    """Collect Vray Proxy instance.

    Add `pointcache` family for it.
    """
    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Vray Proxy"
    families = ["vrayproxy"]

    def process(self, instance):
        """Collector entry point."""
        if not instance.data.get('families'):
            instance.data["families"] = []

        if instance.data.get("vrmesh"):
            instance.data["families"].append("vrayproxy.vrmesh")

        if instance.data.get("alembic"):
            instance.data["families"].append("vrayproxy.alembic")
