import json
import pyblish.api

from openpype.lib import attribute_definitions
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectInstanceOneTestHost(
    pyblish.api.InstancePlugin, OpenPypePyblishPluginMixin
):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Instance 1 - Test Host"
    order = pyblish.api.CollectorOrder - 0.3
    hosts = ["testhost"]

    @classmethod
    def get_attribute_defs(cls):
        return [
            attribute_definitions.NumberDef(
                "version",
                default=1,
                minimum=1,
                maximum=999,
                decimals=0,
                label="Version"
            )
        ]

    def process(self, instance):
        self._debug_log(instance)

        publish_attributes = instance.data.get("publish_attributes")
        if not publish_attributes:
            return

        values = publish_attributes.get(self.__class__.__name__)
        if not values:
            return

        instance.data["version"] = values["version"]

    def _debug_log(self, instance):
        def _default_json(value):
            return str(value)

        self.log.info(
            json.dumps(instance.data, indent=4, default=_default_json)
        )
