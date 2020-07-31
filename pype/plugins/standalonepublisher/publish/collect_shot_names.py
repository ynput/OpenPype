import pyblish.api
import re


class CollectShotNames(pyblish.api.InstancePlugin):
    """
    Collecting shot names
    """

    label = "Collect shot names"
    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["standalonepublisher"]

    def process(self, instance):
        self.log.info("Instance name: `{}`".format(instance.data["name"]))
