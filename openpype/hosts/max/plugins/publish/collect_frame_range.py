# -*- coding: utf-8 -*-
import pyblish.api
from pymxs import runtime as rt


class CollectFrameRange(pyblish.api.InstancePlugin):
    """Collect Frame Range."""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Frame Range"
    hosts = ['max']
    families = ["camera", "maxrender",
                "pointcache", "pointcloud",
                "review", "redshiftproxy"]

    def process(self, instance):
        if instance.data["family"] == "maxrender":
            instance.data["frameStartHandle"] = int(rt.rendStart)
            instance.data["frameEndHandle"] = int(rt.rendEnd)
        else:
            instance.data["frameStartHandle"] = int(rt.animationRange.start)
            instance.data["frameEndHandle"] = int(rt.animationRange.end)
