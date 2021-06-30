import logging
import inspect
import avalon.api
import pyblish.api
from openpype.pipeline import (
    BaseCreator,
    AvalonInstance
)


class PublisherController:
    def __init__(self, headless=False):
        self.log = logging.getLogger("PublisherController")
        self.host = avalon.api.registered_host()
        self.headless = headless

        self.creators = {}
        self.publish_plugins = []
        self.instances = []

        self._in_reset = False

    def reset(self):
        if self._in_reset:
            return

        self._in_reset = True
        self._reset()
        self._in_reset = False

    def _reset(self):
        """Reset to initial state."""
        publish_plugins = pyblish.api.discover()
        self.publish_plugins = publish_plugins

        creators = {}
        for creator in avalon.api.discover(BaseCreator):
            if inspect.isabstract(creator):
                self.log.info(
                    "Skipping abstract Creator {}".format(str(creator))
                )
                continue
            creators[creator.family] = creator

        self.creators = creators

        host_instances = self.host.list_instances()
        instances = []
        for instance_data in host_instances:
            family = instance_data["family"]
            creator = creators.get(family)
            if creator is not None:
                instance_data = creator.convert_family_attribute_values(
                    instance_data
                )
            instance = AvalonInstance.from_existing(instance_data)
            instances.append(instance)

        self.instances = instances
