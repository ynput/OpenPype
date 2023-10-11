import pyblish.api

from openpype.hosts.photoshop import api


class CollectImage(pyblish.api.InstancePlugin):
    """Collect layer metadata into a instance.

    Used later in validation
    """
    order = pyblish.api.CollectorOrder + 0.200
    label = 'Collect Image'

    hosts = ["photoshop"]
    families = ["image"]

    def process(self, instance):
        if instance.data.get("members"):
            layer = api.stub().get_layer(instance.data["members"][0])
            instance.data["layer"] = layer
