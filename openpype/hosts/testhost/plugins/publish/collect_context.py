import pyblish.api

from openpype.pipeline import (
    OpenPypePyblishPluginMixin,
    attribute_definitions
)


class CollectContextDataTestHost(
    pyblish.api.ContextPlugin, OpenPypePyblishPluginMixin
):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Source - Test Host"
    order = pyblish.api.CollectorOrder - 0.4
    hosts = ["testhost"]

    @classmethod
    def get_instance_attr_defs(cls):
        return [
            attribute_definitions.BoolDef(
                "test_bool",
                True,
                label="Bool input"
            )
        ]

    def process(self, context):
        # get json paths from os and load them
        for instance in context:
            instance.data["source"] = "testhost"
