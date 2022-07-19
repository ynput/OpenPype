import os

import pyblish.api


class CollectEditorialReviewable(pyblish.api.InstancePlugin):
    """Collect reviwiewable toggle to instance and representation data
    """

    label = "Collect Editorial Reviewable"
    order = pyblish.api.CollectorOrder

    families = ["plate", "review", "audio"]
    hosts = ["traypublisher"]

    def process(self, instance):
        creator_identifier = instance.data["creator_identifier"]
        if "editorial" not in creator_identifier:
            return

        creator_attributes = instance.data["creator_attributes"]
        repre = instance.data["representations"][0]

        if creator_attributes["add_review_family"]:
            repre["tags"].append("review")
            instance.data["families"].append("review")

        instance.data["representations"] = [repre]

        self.log.debug("instance.data {}".format(instance.data))
