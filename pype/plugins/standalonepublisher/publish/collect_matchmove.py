"""
Requires:
    Nothing

Provides:
    Instance
"""

import pyblish.api
import logging


log = logging.getLogger("collector")


class CollectMatchmovePublish(pyblish.api.InstancePlugin):
    """
    Collector with only one reason for its existence - remove 'ftrack'
    family implicitly added by Standalone Publisher
    """

    label = "Collect Matchmove - SA Publish"
    order = pyblish.api.CollectorOrder
    families = ["matchmove"]
    hosts = ["standalonepublisher"]

    def process(self, instance):
        if "ftrack" in instance.data["families"]:
            instance.data["families"].remove("ftrack")
