import os
import sys
import argparse
import logging

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from pype.clockify import ClockifyAPI


class StartClockify(BaseAction):
    '''Starts timer on clockify.'''

    #: Action identifier.
    identifier = 'clockify.start.timer'
    #: Action label.
    label = 'Clockify - Start timer'
    #: Action description.
    description = 'Starts timer on clockify'
    #: roles that are allowed to register this action
    icon = '{}/app_icons/clockify.png'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )
    #: Clockify api
    clockapi = ClockifyAPI()

    def discover(self, session, entities, event):
        if len(entities) != 1:
            return False
        if entities[0].entity_type.lower() != 'task':
            return False
        if self.clockapi.workspace_id is None:
            return False
        return True

    def launch(self, session, entities, event):
        task = entities[0]
        task_name = task['type']['name']
        project_name = task['project']['full_name']

        def get_parents(entity):
            output = []
            if entity.entity_type.lower() == 'project':
                return output
            output.extend(get_parents(entity['parent']))
            output.append(entity['name'])

            return output

        desc_items = get_parents(task['parent'])
        desc_items.append(task['name'])
        description = '/'.join(desc_items)
        project_id = self.clockapi.get_project_id(project_name)
        tag_ids = []
        tag_ids.append(self.clockapi.get_tag_id(task_name))
        self.clockapi.start_time_entry(
            description, project_id, tag_ids=tag_ids
        )

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    StartClockify(session).register()
