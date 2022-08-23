"""
Taken from https://github.com/tokejepsen/ftrack-hooks/tree/master/batch_tasks
"""

from openpype_modules.ftrack.lib import BaseAction, statics_icon


class BatchTasksAction(BaseAction):
    '''Batch Tasks action
    `label` a descriptive string identifing your action.
    `varaint` To group actions together, give them the same
    label and specify a unique variant per action.
    `identifier` a unique identifier for your action.
    `description` a verbose descriptive text for you action
     '''
    label = "Batch Task Create"
    variant = None
    identifier = "batch-tasks"
    description = None
    icon = statics_icon("ftrack", "action_icons", "BatchTasks.svg")

    def discover(self, session, entities, event):
        '''Return true if we can handle the selected entities.
        *session* is a `ftrack_api.Session` instance
        *entities* is a list of tuples each containing the entity type and the
        entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.
        *event* the unmodified original event
        '''

        not_allowed = ["assetversion", "project", "ReviewSession"]
        if entities[0].entity_type.lower() in not_allowed:
            return False

        return True


    def get_task_form_items(self, session, number_of_tasks):
        items = []

        task_type_options = [
            {'label': task_type["name"], 'value': task_type["id"]}
            for task_type in session.query("Type")
        ]

        for index in range(0, number_of_tasks):
            items.extend(
                [
                    {
                        'value': '##Template for Task{0}##'.format(
                            index
                        ),
                        'type': 'label'
                    },
                    {
                        'label': 'Type',
                        'type': 'enumerator',
                        'name': 'task_{0}_typeid'.format(index),
                        'data': task_type_options
                    },
                    {
                        'label': 'Name',
                        'type': 'text',
                        'name': 'task_{0}_name'.format(index)
                    }
                ]
            )

        return items

    def ensure_task(self, session, name, task_type, parent):

        # Query for existing task.
        query = (
            'Task where type.id is "{0}" and name is "{1}" '
            'and parent.id is "{2}"'
        )
        task = session.query(
            query.format(
                task_type["id"],
                name,
                parent["id"]
            )
        ).first()

        # Create task.
        if not task:
            session.create(
                "Task",
                {
                    "name": name,
                    "type": task_type,
                    "parent": parent
                }
            )

    def launch(self, session, entities, event):
        '''Callback method for the custom action.
        return either a bool ( True if successful or False if the action
        failed ) or a dictionary with they keys `message` and `success`, the
        message should be a string and will be displayed as feedback to the
        user, success should be a bool, True if successful or False if the
        action failed.
        *session* is a `ftrack_api.Session` instance
        *entities* is a list of tuples each containing the entity type and the
        entity id.
        If the entity is a hierarchical you will always get the entity
        type TypedContext, once retrieved through a get operation you
        will have the "real" entity type ie. example Shot, Sequence
        or Asset Build.
        *event* the unmodified original event
        '''
        if 'values' in event['data']:
            values = event['data']['values']
            if 'number_of_tasks' in values:
                return {
                    'success': True,
                    'message': '',
                    'items': self.get_task_form_items(
                        session, int(values['number_of_tasks'])
                    )
                }
            else:
                # Create tasks on each entity
                for entity in entities:
                    for count in range(0, int(len(values.keys()) / 2)):
                        task_type = session.query(
                            'Type where id is "{0}"'.format(
                                values["task_{0}_typeid".format(count)]
                            )
                        ).one()

                        # Get name, or assume task type in lower case as name.
                        name = values["task_{0}_name".format(count)]
                        if not name:
                            name = task_type["name"].lower()

                        self.ensure_task(session, name, task_type, entity)

                session.commit()

                return {
                    'success': True,
                    'message': 'Action completed successfully'
                }

        return {
            'success': True,
            'message': "",
            'items': [
                {
                    'label': 'Number of tasks',
                    'type': 'number',
                    'name': 'number_of_tasks',
                    'value': 2
                }
            ]
        }


def register(session):
    '''Register action. Called when used as an event plugin.'''

    BatchTasksAction(session).register()
