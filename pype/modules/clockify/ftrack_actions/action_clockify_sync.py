import os
import sys
import argparse
import logging
import json
import ftrack_api
from pype.modules.ftrack.lib import BaseAction, MissingPermision
from pype.modules.clockify import ClockifyAPI


class SyncClocify(BaseAction):
    '''Synchronise project names and task types.'''

    #: Action identifier.
    identifier = 'clockify.sync'
    #: Action label.
    label = 'Sync To Clockify'
    #: Action description.
    description = 'Synchronise data to Clockify workspace'
    #: roles that are allowed to register this action
    role_list = ["Pypeclub", "Administrator", "project Manager"]
    #: icon
    icon = '{}/app_icons/clockify-white.png'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )
    #: CLockifyApi
    clockapi = ClockifyAPI()

    def discover(self, session, entities, event):
        if (
            len(entities) == 1
            and entities[0].entity_type.lower() == "project"
        ):
            return True
        return False

    def launch(self, session, entities, event):
        self.clockapi.set_api()
        if self.clockapi.workspace_id is None:
            return {
                "success": False,
                "message": "Clockify Workspace or API key are not set!"
            }

        if self.clockapi.validate_workspace_perm() is False:
            return {
                "success": False,
                "message": "Missing permissions for this action!"
            }

        # JOB SETTINGS
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Sync Ftrack to Clockify'
            })
        })
        session.commit()
        try:
            entity = entities[0]

            if entity.entity_type.lower() == 'project':
                project = entity
            else:
                project = entity['project']
            project_name = project['full_name']

            task_types = []
            for task_type in project['project_schema']['_task_type_schema'][
                'types'
            ]:
                task_types.append(task_type['name'])

            clockify_projects = self.clockapi.get_projects()

            if project_name not in clockify_projects:
                response = self.clockapi.add_project(project_name)
                if 'id' not in response:
                    self.log.error('Project {} can\'t be created'.format(
                        project_name
                    ))
                    return {
                        'success': False,
                        'message': 'Can\'t create project, unexpected error'
                    }
                project_id = response['id']
            else:
                project_id = clockify_projects[project_name]

            clockify_workspace_tags = self.clockapi.get_tags()
            for task_type in task_types:
                if task_type not in clockify_workspace_tags:
                    response = self.clockapi.add_tag(task_type)
                    if 'id' not in response:
                        self.log.error('Task {} can\'t be created'.format(
                            task_type
                        ))
                        continue
        except Exception:
            job['status'] = 'failed'
            session.commit()
            return False

        job['status'] = 'done'
        session.commit()
        return True


def register(session, **kw):
    SyncClocify(session).register()
