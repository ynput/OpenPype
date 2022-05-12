# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class IntegrateKitsuReview(pyblish.api.InstancePlugin):
    """Integrate Kitsu Review"""

    order = pyblish.api.IntegratorOrder + 0.01
    label = "Kitsu Review"
    # families = ["kitsu"]
    optional = True

    def process(self, instance):

        context = instance.context
        task = context.data["kitsu_task"]
        comment = context.data["kitsu_comment"]

        for representation in instance.data.get("representations", []):

            review_path = representation.get("published_path")

            if 'review' not in representation.get("tags", []):
                continue

            self.log.debug("Found review at: {}".format(review_path))

            gazu.task.add_preview(
                task,
                comment,
                review_path,
                normalize_movie=True
            )
            self.log.info("Review upload on comment")
