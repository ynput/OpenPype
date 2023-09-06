"""
Requires:
    None

Provides:
    instance     -> family ("review")
"""
import pyblish.api


class CollectReview(pyblish.api.ContextPlugin):
    """Add review to families if instance created with 'mark_for_review' flag
    """
    label = "Collect Review"
    hosts = ["aftereffects"]
    order = pyblish.api.CollectorOrder + 0.1

    def process(self, context):
        for instance in context:
            creator_attributes = instance.data.get("creator_attributes") or {}
            if (
                creator_attributes.get("mark_for_review")
                and "review" not in instance.data["families"]
            ):
                instance.data["families"].append("review")
