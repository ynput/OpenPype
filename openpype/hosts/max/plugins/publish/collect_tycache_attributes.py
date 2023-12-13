import pyblish.api


class CollectTyCacheData(pyblish.api.InstancePlugin):
    """Collect Channel Attributes for TyCache Export"""

    order = pyblish.api.CollectorOrder + 0.02
    label = "Collect tyCache attribute Data"
    hosts = ['max']
    families = ["tycache", "tyspline"]

    def process(self, instance):
        family  = instance.data["family"]
        instance.data["exportMode"] = 2 if family == "tycache" else 6
