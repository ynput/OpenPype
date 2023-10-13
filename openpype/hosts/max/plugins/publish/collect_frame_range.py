# -*- coding: utf-8 -*-
"""Collect instance members."""
import pyblish.api
from pymxs import runtime as rt


class CollectFrameRange(pyblish.api.InstancePlugin):
    """Collect Set Members."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Frame Range"
    hosts = ['max']
    families = ["camera", "maxrender",
                "pointcache", "pointcloud",
                "review"]

    def process(self, instance):
        if instance.data["family"] == "maxrender":
            instance.data["frameStart"] = int(rt.rendStart)
            instance.data["frameEnd"] = int(rt.rendEnd)
        else:
            instance.data["frameStart"] = int(rt.animationRange.start)
            instance.data["frameEnd"] = int(rt.animationRange.end)
