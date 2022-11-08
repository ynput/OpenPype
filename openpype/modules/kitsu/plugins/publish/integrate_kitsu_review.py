# -*- coding: utf-8 -*-
import os
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
        comment = context.data.get("kitsu_comment")

        # Check comment has been created
        if not comment:
            self.log.debug(
                "Comment not created, review not pushed to preview."
            )
            return

        # Add review representations as preview of comment
        for representation in instance.data.get("representations", []):
            # Skip if not tagged as review
            if "review" not in representation.get("tags", []):
                continue

            review_path = representation.get("published_path")
            file_name, file_extension = os.path.splitext(review_path)

            if instance.data.get('name') != 'reviewMain' \
                    or file_extension != '.mp4':
                continue

            self.log.debug("Found review at: {}".format(review_path))
            gazu.task.add_preview(
                task, comment, review_path, normalize_movie=True
            )
            self.log.info("Review upload on comment")
