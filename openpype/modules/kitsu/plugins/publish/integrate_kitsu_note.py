# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class IntegrateKitsuNote(pyblish.api.ContextPlugin):
    """Integrate Kitsu Note"""

    order = pyblish.api.IntegratorOrder
    label = "Kitsu Note and Status"
    # families = ["kitsu"]

    def process(self, context):
        # Check if work version for user
        is_work_version = bool(context.data.get("intent", {}).get("value"))
        if is_work_version:
            self.log.info("Work version, nothing pushed to Kitsu.")
            return

        # Get comment text body
        publish_comment = context.data.get("comment")
        if not publish_comment:
            self.log.info("Comment is not set.")

        self.log.debug("Comment is `{}`".format(publish_comment))

        # Get Waiting for Approval status
        kitsu_status = gazu.task.get_task_status_by_short_name("wfa")
        if not kitsu_status:
            self.log.info(
                "Cannot find 'Waiting For Approval' status."
                "The status will not be changed"
            )
            kitsu_status = context.data["kitsu_task"].get("task_status")
        self.log.debug("Kitsu status: {}".format(kitsu_status))

        # Add comment to kitsu task
        kitsu_comment = gazu.task.add_comment(
            context.data["kitsu_task"], kitsu_status, comment=publish_comment
        )

        context.data["kitsu_comment"] = kitsu_comment
