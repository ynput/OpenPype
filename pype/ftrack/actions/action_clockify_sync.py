import sys
import argparse
import logging
import json
import ftrack_api
from pype.ftrack import BaseAction
from pype.clockify import ClockifyAPI


class SyncClocify(BaseAction):
    '''Synchronise project names and task types.'''

    #: Action identifier.
    identifier = 'clockify.sync'
    #: Action label.
    label = 'Sync To Clockify'
    #: Action description.
    description = 'Synchronise data to Clockify workspace'
    #: priority
    priority = 100
    #: roles that are allowed to register this action
    role_list = ['Pypecub', 'Administrator']
    #: icon
    icon = 'https://clockify.me/assets/images/clockify-logo-white.svg'
    #: CLockifyApi
    clockapi = ClockifyAPI()

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def validate_auth_rights(self):
        test_project = '__test__'
        try:
            self.clockapi.add_project(test_project)
        except Exception:
            return False
        self.clockapi.delete_project(test_project)
        return True

    def launch(self, session, entities, event):
        authorization = self.validate_auth_rights()
        if authorization is False:
            return {
                'success': False,
                'message': (
                    'You don\'t have permission to modify Clockify'
                    ' workspace {}'.format(self.clockapi.workspace)
                )
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
            projects_info = {}
            for project in session.query('Project').all():
                task_types = []
                for task_type in project['project_schema']['_task_type_schema'][
                    'types'
                ]:
                    task_types.append(task_type['name'])
                projects_info[project['full_name']] = task_types

            clockify_projects = self.clockapi.get_projects()
            for project_name, task_types in projects_info.items():
                if project_name not in clockify_projects:
                    response = self.clockapi.add_project(project_name)
                    if 'id' not in response:
                        self.log.error('Project {} can\'t be created'.format(
                            project_name
                        ))
                        continue
                    project_id = response['id']
                else:
                    project_id = clockify_projects[project_name]

                clockify_project_tasks = self.clockapi.get_tasks(
                    project_id=project_id
                )
                for task_type in task_types:
                    if task_type not in clockify_project_tasks:
                        response = self.clockapi.add_task(
                            task_type, project_id=project_id
                        )
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
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    SyncClocify(session).register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
