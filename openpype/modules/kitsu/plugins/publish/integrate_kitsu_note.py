import gazu
import pyblish.api


class IntegrateKitsuNote(pyblish.api.ContextPlugin):
    """Integrate Kitsu Note"""

    order = pyblish.api.IntegratorOrder
    label = "Kitsu Note and Status"
    # families = ["kitsu"]
    optional = True

    def process(self, context):

        publish_comment = context.data.get("comment")
        if not publish_comment:
            self.log.info("Comment is not set.")

        publish_status = context.data.get("intent", {}).get("value")
        if not publish_status:
            self.log.info("Status is not set.")

        self.log.debug("Comment is `{}`".format(publish_comment))
        self.log.debug("Status is `{}`".format(publish_status))

        kitsu_status = context.data.get("kitsu_status")
        if not kitsu_status:
            self.log.info("The status will not be changed")
            kitsu_status = context.data["kitsu_task"].get("task_status")
        self.log.debug("Kitsu status: {}".format(kitsu_status))

        gazu.task.add_comment(
            context.data["kitsu_task"], 
            kitsu_status, 
            comment = publish_comment
        )