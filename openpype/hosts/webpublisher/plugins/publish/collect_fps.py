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
        fps = instance.context.data["fps"]

        instance.data.update({
            "fps": fps
        })
        self.log.debug(f"instance.data: {pformat(instance.data)}")
