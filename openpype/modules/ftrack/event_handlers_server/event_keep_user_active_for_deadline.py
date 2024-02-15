import ftrack_api
from openpype_modules.ftrack.lib import BaseEvent
from openpype.modules import ModulesManager


class KeepUserActiveForDeadline(BaseEvent):

    def launch(self, session, event):
        """Ensure the user stays active while having ongoing job(s) in the Deadline."""
        if not event.get('data'):
            return

        entities_info = event['data'].get('entities')
        if not entities_info:
            return

        entity_info = entities_info[0]
        # check if a user has been deactivated
        if entity_info.get('entity_type') != "User":
            return
        if entity_info.get('action', "") != "update":
            return
        if "isactive" not in entity_info.get('changes', {}):
            return
        if entity_info['changes']['isactive'].get('new') != False:
            return

        user = session.get('User', entity_info.get('entityId'))
        if not user:
            return

        job_ids = self.get_user_active_deadline_jobs(user['username'])
        if not job_ids:
            return

        # activate the account
        user['is_active'] = True
        session.commit()
        self.log.info("the user {} has been re-activated".format(user['username']))

        # Return the issue message form
        items = [
            {
                "type": "label",
                "value": "#Warning: The user has been re-activated!"
            },
            {
                "type": "label",
                "value": "The following jobs from this user are currently active "
                         "on deadline:\n{}".format("\n".join(job_ids))
            },
            {
                "type": "label",
                "value": "Please try later when all the jobs are done."
            }
        ]

        self.show_interface(
            items,
            title="The User Must Remain Active",
            event=event,
            submit_btn_label="I will try later!"
        )
        return True

    def get_user_active_deadline_jobs(self, user):
        """Get all active deadline jobs of the user
        """
        manager = ModulesManager()
        deadline_module = manager.modules_by_name["deadline"]
        deadline_url = deadline_module.deadline_urls["default"]

        if not deadline_url:
            self.log.info("Deadline URL not found, skipping.")
            return

        requested_arguments = {
            "States": "Active"
        }

        jobs = deadline_module.get_deadline_data(
            deadline_url,
            "jobs",
            log=None,
            **requested_arguments
        )

        user_jobs = []
        for job in jobs:
            if job['Props']['Env'].get('FTRACK_API_USER') == user:
                user_jobs.append(job['_id'])

        return user_jobs


def register(session):
    """Register plugin. Called when used as an plugin."""
    KeepUserActiveForDeadline(session).register()
