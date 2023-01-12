import pyblish.api
from openpype.lib.attribute_definitions import TextDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectFramesFixDef(
    pyblish.api.ContextPlugin,
    OpenPypePyblishPluginMixin
):
    label = "Collect frames to fix"
    targets = ["local"]
    # Disable plugin by default
    families = ["render"]
    enabled = True

    def process(self, instance):
        attribute_values = self.get_attr_values_from_data(instance.data)
        frames_to_fix = attribute_values.get("frames_to_fix")
        if frames_to_fix:
            instance.data["frames_to_fix"] = frames_to_fix

    @classmethod
    def get_attribute_defs(cls):
        return [
            TextDef("frames_to_fix", label="Frames to fix",
                    placeholder="5,10-15",
                    regex="[0-9,-]+")
        ]

