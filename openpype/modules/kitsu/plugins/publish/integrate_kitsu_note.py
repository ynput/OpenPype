# -*- coding: utf-8 -*-
import gazu
import pyblish.api
import re


class IntegrateKitsuNote(pyblish.api.ContextPlugin):
    """Integrate Kitsu Note"""

    order = pyblish.api.IntegratorOrder
    label = "Kitsu Note and Status"
    families = ["render", "kitsu"]

    # status settings
    set_status_note = False
    note_status_shortname = "wfa"

    # comment settings
    custom_comment_template = {
        "enabled": False,
        "comment_template": "{comment}",
    }

    def format_publish_comment(self, instance):
        """Format the instance's publish comment

        Formats `instance.data` against the custom template.
        """
        
        def replace_missing_key(match):
            """If key is not found in kwargs, set None instead"""
            key = match.group(1)
            if key not in instance.data:
                self.log.warning(
                    "Key "{}" was not found in instance.data "
                    "and will be rendered as "" in the comment".format(key)
                )
                return ""
            else:
                return str(instance.data[key])

        template = self.custom_comment_template["comment_template"]
        pattern = r"\{([^}]*)\}"
        return re.sub(pattern, replace_missing_key, template)

    def process(self, context):
        # Get comment text body
        publish_comment = context.data.get("comment")
        if not publish_comment:
            self.log.info("Comment is not set.")

        for instance in context:
            # Check if instance is a review by checking its family
            if "review" not in instance.data["families"]:
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

            # If custom comment, create it
            if self.custom_comment_template["enabled"]:
                publish_comment = self.format_publish_comment(instance)

            self.log.debug("Comment is `{}`".format(publish_comment))

            # Add comment to kitsu task
            task_id = kitsu_task["id"]
            self.log.debug("Add new note in taks id {}".format(task_id))
            kitsu_comment = gazu.task.add_comment(
                task_id, note_status, comment=publish_comment
            )

            instance.data["kitsu_comment"] = kitsu_comment
