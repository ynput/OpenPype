import ftrack_api
from openpype_modules.ftrack.lib import BaseEvent
from openpype.modules.deadline.deadline_module import DeadlineModule


class KeepUserActiveForDeadline(BaseEvent):

    def launch(self, session, event):
        '''Ensure the user stays active while having an ongoing job in the Deadline.'''
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
        if not "isactive" in entity_info.get('changes', {}):
            return
        if entity_info['changes']['isactive'].get('new') != False:
            return

        user = session.get('User', entity_info.get('entityId'))
        if not user:
            return

        job_ids = self.get_user_active_deadline_jobs(user)
        if job_ids:
            # activate the account
            user['is_active'] = True
            session.commit()
            # Return the issue message form
            return {
                "type": "form",
                "items": [
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
                ],
                "title": "Create Project Structure",
                "submit_button_label": "I will do the changes"
            }

    def get_user_active_deadline_jobs(self, user):
        """Get all active deadline jobs of the user
        """
        deadline_url = "http://deadline.prs.vfx.int:8081"

        requested_arguments = {
            # "IdOnly": True,
            "States":"Active"
        }

        jobs = DeadlineModule.get_deadline_data(
            deadline_url,
            "jobs",
            log=None,
            **requested_arguments
        )

        user_jobs = [job['_id'] for job in jobs if job['Props']['User']==user]

        return user_jobs

def register(session):
    '''Register plugin. Called when used as an plugin.'''
    KeepUserActiveForDeadline(session).register()
