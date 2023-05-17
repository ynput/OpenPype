# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class IntegrateKitsuReview(pyblish.api.InstancePlugin):
    """Integrate Kitsu Review"""

    order = pyblish.api.IntegratorOrder + 0.01
    label = "Kitsu Review"
    families = ["render", "image", "online", "plate", "kitsu"]
    optional = True

    def process(self, instance):
        # Check comment has been created
        comment_id = instance.data.get("kitsu_comment", {}).get("id")
        if not comment_id:
            self.log.debug(
                "Comment not created, review not pushed to preview."
            )
            return

        # Add review representations as preview of comment
        task_id = instance.data["kitsu_task"]["id"]
        for representation in instance.data.get("representations", []):
            # Skip if not tagged as review
            if "kitsureview" not in representation.get("tags", []):
                continue
            review_path = representation.get("published_path")
            self.log.debug("Found review at: {}".format(review_path))

            gazu.task.add_preview(
                task_id, comment_id, review_path, normalize_movie=True
            )
            self.log.info("Review upload on comment")
