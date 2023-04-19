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
    """Collect or create review instance.

    Review instance might be autocreated or needs to be created if non artist
    based workflow is used (eg. Webpublisher)
    """

    label = "Collect Review"
    label = "Review"
    hosts = ["photoshop"]
    order = pyblish.api.CollectorOrder + 0.1

    publish = True

    def process(self, context):
        family = "review"
        has_review = False
        for instance in context:
            if instance.data["family"] == family:
                has_review = True

            creator_attributes = instance.data["creator_attributes"]
            if (creator_attributes.get("mark_for_review") and
                    "review" not in instance.data["families"]):
                instance.data["families"].append("review")

        # additional logic only for remote publishing from Webpublisher
        if "remotepublish" not in pyblish.api.registered_targets():
            return

        if has_review:
            self.log.debug("Review instance found, won't create new")
            return

        subset = get_subset_name(
            family,
            context.data.get("variant", ''),
            context.data["anatomyData"]["task"]["name"],
            context.data["assetEntity"],
            context.data["anatomyData"]["project"]["name"],
            host_name=context.data["hostName"],
            project_settings=context.data["project_settings"]
        )

        instance = context.create_instance(subset)
        instance.data.update({
            "subset": subset,
            "label": subset,
            "name": subset,
            "family": family,
            "families": [],
            "representations": [],
            "asset": os.environ["AVALON_ASSET"],
            "publish": self.publish
        })
