import sys
import argparse
import logging
import json
import ftrack_api
from pype.ftrack import BaseAction, MissingPermision
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
    role_list = ['Pypeclub', 'Administrator']
    #: icon
    icon = 'https://clockify.me/assets/images/clockify-logo-white.svg'
    #: CLockifyApi
    clockapi = ClockifyAPI()

    def register(self):
        if self.validate_auth_rights() is False:
            raise MissingPermision
        super().register()

    def validate_auth_rights(self):
        test_project = '__test__'
        try:
            self.clockapi.add_project(test_project)
        except Exception:
            return False
        self.clockapi.delete_project(test_project)
        return True

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def interface(self, session, entities, event):
        if not event['data'].get('values', {}):
            title = 'Select projects to sync'

            projects = session.query('Project').all()

            items = []
            all_projects_label = {
                'type': 'label',
                'value': 'All projects'
            }
            all_projects_value = {
                'name': '__all__',
                'type': 'boolean',
                'value': False
            }
            line = {
                'type': 'label',
                'value': '___'
            }
            items.append(all_projects_label)
            items.append(all_projects_value)
            items.append(line)
            for project in projects:
                label = project['full_name']
                item_label = {
                    'type': 'label',
                    'value': label
                }
                item_value = {
                    'name': project['id'],
                    'type': 'boolean',
                    'value': False
                }
                items.append(item_label)
                items.append(item_value)

            return {
                'items': items,
                'title': title
            }

    def launch(self, session, entities, event):
        values = event['data'].get('values', {})
        if not values:
            return

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
            if values.get('__all__', False) is True:
                projects_to_sync = session.query('Project').all()
            else:
                projects_to_sync = []
                project_query = 'Project where id is "{}"'
                for project_id, sync in values.items():
                    if sync is True:
                        projects_to_sync.append(session.query(
                            project_query.format(project_id)
                        ).one())

            projects_info = {}
            for project in projects_to_sync:
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
