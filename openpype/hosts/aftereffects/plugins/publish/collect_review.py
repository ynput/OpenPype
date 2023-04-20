"""
Requires:
    None

Provides:
    instance     -> family ("review")
"""
import pyblish.api


class CollectReview(pyblish.api.InstancePlugin):
    """Add review to families if instance created with 'mark_for_review' flag
    """

    label = "Collect Review"
    label = "Review"
    hosts = ["aftereffects"]
    order = pyblish.api.CollectorOrder + 0.1

    publish = True

    def process(self, instance):
        creator_attributes = instance.data.get("creator_attributes")
        if (creator_attributes and
                creator_attributes.get("mark_for_review") and
                "review" not in instance.data["families"]):
            instance.data["families"].append("review")
