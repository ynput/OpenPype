import pyblish.api

from openpype.hosts.photoshop import api as photoshop


class CollectAutoImageRefresh(pyblish.api.ContextPlugin):
    """Refreshes auto_image instance with currently visible layers..
    """

    label = "Collect Auto Image Refresh"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    order = pyblish.api.CollectorOrder + 0.2

    def process(self, context):
        for instance in context:
            creator_identifier = instance.data.get("creator_identifier")
            if creator_identifier and creator_identifier == "auto_image":
                self.log.debug("Auto image instance found, won't create new")
                # refresh existing auto image instance with current visible
                publishable_ids = [layer.id for layer in photoshop.stub().get_layers()  # noqa
                                   if layer.visible]
                instance.data["ids"] = publishable_ids
                return
