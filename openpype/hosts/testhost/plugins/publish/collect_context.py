import pyblish.api
from avalon import io

from openpype.hosts.testhost import api
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

    label = "Collect Context - Test Host"
    order = pyblish.api.CollectorOrder - 0.5
    hosts = ["testhost"]

    @classmethod
    def get_attribute_defs(cls):
        return [
            attribute_definitions.BoolDef(
                "test_bool",
                True,
                label="Bool input"
            )
        ]

    def process(self, context):
        # get json paths from os and load them
        io.install()

        for instance_data in api.list_instances():
            # create instance
            self.create_instance(context, instance_data)

    def create_instance(self, context, in_data):
        subset = in_data["subset"]
        # If instance data already contain families then use it
        instance_families = in_data.get("families") or []

        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "asset": in_data["asset"],
            "label": subset,
            "name": subset,
            "family": in_data["family"],
            "families": instance_families
        })
        for key, value in in_data.items():
            if key not in instance.data:
                instance.data[key] = value
        self.log.info("collected instance: {}".format(instance.data))
        self.log.info("parsing data: {}".format(in_data))

        instance.data["representations"] = list()
        instance.data["source"] = "testhost"
