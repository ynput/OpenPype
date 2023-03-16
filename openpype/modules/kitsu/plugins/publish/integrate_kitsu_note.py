# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class IntegrateKitsuNote(pyblish.api.ContextPlugin):
    """Integrate Kitsu Note"""

    order = pyblish.api.IntegratorOrder
    label = "Kitsu Note and Status"
    families = ["render", "review"]
    set_status_note = False
    note_status_shortname = "wfa"

    def process(self, context):
        # Get comment text body
        publish_comment = context.data.get("comment")
        if not publish_comment:
            self.log.info("Comment is not set.")

        self.log.debug("Comment is `{}`".format(publish_comment))

        for instance in context:
            # Skip if not in families
            if instance.data.get("family") not in self.families:
                continue

            kitsu_task = instance.data.get("kitsu_task")
            if kitsu_task is None:
                continue

            # Get note status, by default uses the task status for the note
            # if it is not specified in the configuration
            note_status = kitsu_task["task_status"]["id"]

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
            task_id = kitsu_task["id"]
            self.log.debug("Add new note in taks id {}".format(task_id))
            kitsu_comment = gazu.task.add_comment(
                task_id, note_status, comment=publish_comment
            )

            instance.data["kitsu_comment"] = kitsu_comment
