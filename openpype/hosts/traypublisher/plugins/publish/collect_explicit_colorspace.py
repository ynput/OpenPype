import pyblish.api

from openpype.pipeline import publish
from openpype.lib import TextDef


class CollectColorspace(pyblish.api.InstancePlugin,
                        publish.OpenPypePyblishPluginMixin,
                        publish.ColormanagedPyblishPluginMixin):
    """Collect explicit user defined representation colorspaces"""

    label = "Choose representation colorspace"
    order = pyblish.api.CollectorOrder + 0.49
    hosts = ["traypublisher"]

    def process(self, instance):
        values = self.get_attr_values_from_data(instance.data)
        colorspace = values.get("colorspace", None)
        if not colorspace:
            return

        context = instance.context
        for repre in instance.data.get("representations", {}):
            self.set_representation_colorspace(
                representation=repre,
                context=context,
                colorspace=colorspace
            )

    @classmethod
    def get_attribute_defs(cls):
        return [
            TextDef("colorspace",
                    label="Override Colorspace",
                    placeholder="")
        ]
