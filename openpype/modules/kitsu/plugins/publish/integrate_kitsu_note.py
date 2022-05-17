# -*- coding: utf-8 -*-
from distutils.log import debug
import gazu
import pyblish.api


class IntegrateKitsuNote(pyblish.api.ContextPlugin):
    """Integrate Kitsu Note"""

    order = pyblish.api.IntegratorOrder
    label = "Kitsu Note and Status"
    # families = ["kitsu"]
    set_status_note = False
    note_status_shortname = "wfa"

    def process(self, context):

        # Get comment text body
        publish_comment = context.data.get("comment")
        if not publish_comment:
            self.log.info("Comment is not set.")

        self.log.debug("Comment is `{}`".format(publish_comment))

        # Get note status, by default uses the task status for the note
        # if it is not specified in the configuration
        note_status = context.data["kitsu_task"]["task_status_id"]
        if self.set_status_note:
            kitsu_status = gazu.task.get_task_status_by_short_name(
                self.note_status_shortname
            )
            if kitsu_status:
                note_status = kitsu_status
                self.log.info("Note Kitsu status: {}".format(note_status))
            else:
                self.log.info(
                    "Cannot find {} status. The status will not be "
                    "changed!".format(self.note_status_shortname)
                )

        # Add comment to kitsu task
        self.log.debug(
            "Add new note in taks id {}".format(
                context.data["kitsu_task"]["id"]
            )
        )
        kitsu_comment = gazu.task.add_comment(
            context.data["kitsu_task"], note_status, comment=publish_comment
        )

        context.data["kitsu_comment"] = kitsu_comment
