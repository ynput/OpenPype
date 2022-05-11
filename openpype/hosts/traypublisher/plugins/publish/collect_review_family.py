import pyblish.api
from openpype.lib import BoolDef
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectReviewFamily(
    pyblish.api.InstancePlugin, OpenPypePyblishPluginMixin
):
    """Add review family."""

    label = "Collect Review Family"
    order = pyblish.api.CollectorOrder - 0.49

    hosts = ["traypublisher"]
    families = [
        "image",
        "render",
        "plate",
        "review"
    ]

    def process(self, instance):
        values = self.get_attr_values_from_data(instance.data)
        if values.get("add_review_family"):
            instance.data["families"].append("review")

    @classmethod
    def get_attribute_defs(cls):
        return [
            BoolDef("add_review_family", label="Review", default=True)
        ]
