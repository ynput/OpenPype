"""
Requires:
    None

Provides:
    instance     -> family ("review")
"""

import os

import pyblish.api

from openpype.pipeline.create import get_subset_name


class CollectReview(pyblish.api.ContextPlugin):
    """Adds review to families for instances marked to be reviewable.
    """

    label = "Collect Review"
    label = "Review"
    hosts = ["photoshop"]
    order = pyblish.api.CollectorOrder + 0.1

    publish = True

    def process(self, context):
        for instance in context:
            creator_attributes = instance.data["creator_attributes"]
            if (creator_attributes.get("mark_for_review") and
                    "review" not in instance.data["families"]):
                instance.data["families"].append("review")
