import json
from openpype_modules.ftrack.lib import BaseAction, statics_icon


class JobKiller(BaseAction):
    """Kill jobs that are marked as running."""

    identifier = "job.killer"
    label = "OpenPype Admin"
    variant = "- Job Killer"
    description = "Killing selected running jobs"
    icon = statics_icon("ftrack", "action_icons", "OpenPypeAdmin.svg")
    settings_key = "job_killer"

    def discover(self, session, entities, event):
        """Check if action is available for user role."""
        return self.valid_roles(session, entities, event)

    def interface(self, session, entities, event):
        if event["data"].get("values"):
            return

        title = "Select jobs to kill"

        jobs = session.query(
            "select id, user_id, status, created_at, data from Job"
            " where status in (\"queued\", \"running\")"
        ).all()
        if not jobs:
            return {
                "success": True,
                "message": "Didn't found any running jobs"
            }

        # Collect user ids from jobs
        user_ids = set()
        for job in jobs:
            user_id = job["user_id"]
            if user_id:
                user_ids.add(user_id)

        # Store usernames by their ids
        usernames_by_id = {}
        if user_ids:
            users = session.query(
                "select id, username from User where id in ({})".format(
                    self.join_query_keys(user_ids)
                )
            ).all()
            for user in users:
                usernames_by_id[user["id"]] = user["username"]

        items = []
        for job in jobs:
            try:
                data = json.loads(job["data"])
                desctiption = data["description"]
            except Exception:
                desctiption = "*No description*"
            user_id = job["user_id"]
            username = usernames_by_id.get(user_id) or "Unknown user"
            created = job["created_at"].strftime('%d.%m.%Y %H:%M:%S')
            label = "{} - {} - {}".format(
                username, desctiption, created
            )
            item_label = {
                "type": "label",
                "value": label
            }
            item = {
                "name": job["id"],
                "type": "boolean",
                "value": False
            }
            if len(items) > 0:
                items.append({"type": "label", "value": "---"})
            items.append(item_label)
            items.append(item)

        return {
            "items": items,
            "title": title
        }

    def launch(self, session, entities, event):
        if "values" not in event["data"]:
            return

        values = event["data"]["values"]
        if len(values) < 1:
            return {
                "success": True,
                "message": "No jobs to kill!"
            }

        job_ids = set()
        for job_id, kill_job in values.items():
            if kill_job:
                job_ids.add(job_id)

        jobs = session.query(
            "select id, status from Job where id in ({})".format(
                self.join_query_keys(job_ids)
            )
        ).all()

        # Update all the queried jobs, setting the status to failed.
        for job in jobs:
            try:
                origin_status = job["status"]
                self.log.debug((
                    'Changing Job ({}) status: {} -> failed'
                ).format(job["id"], origin_status))

                job["status"] = "failed"
                session.commit()

            except Exception:
                session.rollback()
                self.log.warning((
                    "Changing Job ({}) has failed"
                ).format(job["id"]))

        self.log.info("All selected jobs were killed Successfully!")
        return {
            "success": True,
            "message": "All selected jobs were killed Successfully!"
        }


def register(session):
    '''Register plugin. Called when used as an plugin.'''

    JobKiller(session).register()
