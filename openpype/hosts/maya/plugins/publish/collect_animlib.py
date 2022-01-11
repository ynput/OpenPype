import pyblish.api


class CollectAnimLibData(pyblish.api.InstancePlugin):
    """Collect animlib data

    Ensures animlibs are published.

    """

    order = pyblish.api.CollectorOrder
    label = 'Collect AnimLib Data'
    families = ["animlib"]

    def process(self, instance):
        pass
