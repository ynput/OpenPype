"""
Requires:
    Nothing

Provides:
    Instance
"""

import pyblish.api
from pprint import pformat


class CollectInstanceData(pyblish.api.InstancePlugin):
    """
    Collector with only one reason for its existence - remove 'ftrack'
    family implicitly added by Standalone Publisher
    """

    label = "Collect instance data"
    order = pyblish.api.CollectorOrder + 0.49
    families = ["render", "plate"]
    hosts = ["standalonepublisher"]

    def process(self, instance):
        fps = instance.data["assetEntity"]["data"]["fps"]
        instance.data.update({
            "fps": fps
        })
        self.log.debug(f"instance.data: {pformat(instance.data)}")
