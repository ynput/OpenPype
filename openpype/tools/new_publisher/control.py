import logging
import inspect
import avalon.api
from openpype.pipeline import BaseCreator


class PublisherController:
    def __init__(self):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()

        self.creators = []
        self.publish_plugins = []
        self.instances = []

    def reset(self):
        """Reset to initial state."""
        creators = []
        for creator in avalon.api.discover(BaseCreator):
            if inspect.isabstract(creator):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(creator))
                )
                continue
            creators.append(creator)

        self.creators = creators
        self.publish_plugins = []

        self.instances = self.host.list_instances()
