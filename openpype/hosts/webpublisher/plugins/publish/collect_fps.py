"""
Requires:
    Nothing

Provides:
    Instance
"""

import pyblish.api
from pprint import pformat


class CollectFPS(pyblish.api.InstancePlugin):
    """
        Adds fps from context to instance because of ExtractReview
    """

    label = "Collect fps"
    order = pyblish.api.CollectorOrder + 0.49
    hosts = ["webpublisher"]

    def process(self, instance):
        instance_fps = instance.data.get("fps")
        if instance_fps is None:
            instance.data["fps"] = instance.context.data["fps"]

        self.log.debug(f"instance.data: {pformat(instance.data)}")
