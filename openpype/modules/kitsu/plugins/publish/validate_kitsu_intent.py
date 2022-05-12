# -*- coding: utf-8 -*-
import pyblish.api
import gazu


class ValidateKitsuIntent(pyblish.api.ContextPlugin):
    """Validate Kitsu Status"""

    order = pyblish.api.ValidatorOrder
    label = "Kitsu Intent/Status"
    # families = ["kitsu"]
    optional = True

    def process(self, context):
        # Check publish status exists
        publish_status = context.data.get("intent", {}).get("value")
        if not publish_status:
            self.log.info("Status is not set.")
            return

        kitsu_status = gazu.task.get_task_status_by_short_name(publish_status)
        if not kitsu_status:
            raise AssertionError(
                "Status `{}` not found in kitsu!".format(kitsu_status)
            )
        self.log.debug("Collect kitsu status: {}".format(kitsu_status))

        context.data["kitsu_status"] = kitsu_status
