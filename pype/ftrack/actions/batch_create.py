# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack
import sys
import argparse
import logging
import collections
import threading
import getpass
import ftrack_api
from ftrack_action_handler import BaseAction

STRUCTURE_NAMES = ['episode', 'sequence', 'shot']


TASK_TYPE_ENUMERATOR_OPTIONS = [
    {'label': task_type.getName(), 'value': task_type.getId()}
    for task_type in ftrack.getTaskTypes()
]

TASK_TYPE_LOOKUP = dict(
    (task_type.getId(), task_type.getName())
    for task_type in ftrack.getTaskTypes()
)


def async(fn):
    '''Run *fn* asynchronously.'''
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
    return wrapper


def get_names(base_name, padding, start, end, incremental):
    '''Return names from expression.'''
    names = []
    for part in range(start, end + incremental, incremental):
        names.append(
            base_name + str(part).zfill(padding)
        )
    return names


def generate_structure(values):
    '''Return structure from *values*.'''
    structure = []

    for structure_name in STRUCTURE_NAMES:
        if (structure_name + '_expression') not in values:
            continue

        object_expression = values[structure_name + '_expression']
        object_incremental = values[structure_name + '_incremental']

        padding = object_expression.count('#')
        _range, incremental = object_incremental.split(':')
        start, end = _range.split('-')

        start = int(start)
        end = int(end)
        incremental = int(incremental)

        base_name = object_expression.replace('#', '')

        logging.info(
            (
                'Create from expression {expression} with {base_name}, '
                '{padding} and {start}-{end}:{incremental}'
            ).format(
                expression=object_expression,
                base_name=base_name,
                padding=padding,
                start=start,
                end=end,
                incremental=incremental
            )
        )

        names = get_names(
            base_name=base_name,
            padding=padding,
            start=start,
            end=end,
            incremental=incremental
        )

        structure.append({
            'object_type': structure_name,
            'data': names
        })

    tasks = collections.defaultdict(dict)
    for name, value in values.iteritems():
        if name.startswith('task_'):
            _, index, key = name.split('_')
            if key == 'bid' and value:
                value = float(value) * 3600
            tasks[index][key] = value

    task_data = []
    structure.append({
        'object_type': 'task',
        'data': task_data
    })
    for task in tasks.values():
        task_data.append(task)

    return structure


@async
def create(parent, structure):
    '''Create *structure* under *parent*.'''
    return create_from_structure(parent, structure)


def create_from_structure(parent, structure):
    '''Create *structure* under *parent*.'''
    level = structure[0]
    children = structure[1:]
    object_type = level['object_type']

    for data in level['data']:

        if object_type == 'episode':
            new_object = parent.createEpisode(data)

        if object_type == 'sequence':
            new_object = parent.createSequence(data)

        if object_type == 'shot':
            new_object = parent.createShot(data)

        if object_type == 'task':
            new_object = parent.createTask(
                TASK_TYPE_LOOKUP[data['typeid']]
            )
            new_object.set(data)

        logging.info(
            'Created {new_object} on parent {parent}'.format(
                parent=parent, new_object=new_object
            )
        )
        if children:
            create_from_structure(new_object, children)


def get_form(number_of_tasks, structure_type, prefix, padding_count):
    '''Return form from *number_of_tasks* and *structure_type*.'''
    mappings = {
        'episode': ['episode', 'sequence', 'shot'],
        'sequence': ['sequence', 'shot'],
        'shot': ['shot']
    }

    items = []

    for structure_name in mappings[structure_type]:
        items.extend(
            [
                {
                    'value': '##{0}##'.format(structure_name.capitalize()),
                    'type': 'label'
                }, {
                    'label': 'Expression',
                    'type': 'text',
                    'value': prefix + '#' * padding_count,
                    'name': '{0}_expression'.format(structure_name)
                }, {
                    'label': 'Incremental',
                    'type': 'text',
                    'value': '10-20:10',
                    'name': '{0}_incremental'.format(structure_name)
                }
            ]
        )

    for index in range(0, number_of_tasks):
        items.extend(
            [
                {
                    'value': '##Template for Task{0}##'.format(index),
                    'type': 'label'
                },
                {
                    'label': 'Type',
                    'type': 'enumerator',
                    'name': 'task_{0}_typeid'.format(index),
                    'data': TASK_TYPE_ENUMERATOR_OPTIONS
                },
                {
                    'label': 'Bid',
                    'type': 'number',
                    'name': 'task_{0}_bid'.format(index)
                }
            ]
        )

    return {'items': items}


class BatchCreate(BaseAction):
    '''Batch create objects in ftrack.'''

    #: Action identifier.
    identifier = 'batch_create'
    #: Action label.
    label = 'Batch create'
    
    def discover(self, session, entities, event):

        if (len(entities) != 1 or entities[0].entity_type.lower()
            not in ['project', 'episode', 'sequence']):
            return False

        return True

    def interface(self, session, entities, event):
        if 'values' not in event['data']:
            data = [
                {
                    'label': 'Episode, Sequence, Shot',
                    'value': 'episode'
                }, {
                    'label': 'Sequence, Shot',
                    'value': 'sequence'
                }, {
                    'label': 'Shot',
                    'value': 'shot'
                }
            ]
            entity = None
            data_value = 'episode'
            entity_name = ''
            try:
                entity = ftrack.Project(selection[0]['entityId'])
                entity_name = entity.getFullName()
            except:
                pass
            try:
                entity = ftrack.Task(selection[0]['entityId'])
                object_type = entity.getObjectType()
                entity_name = entity.getName()

                if object_type == 'Episode':
                    del data[0]
                    data_value = 'sequence'

                if object_type == 'Sequence':
                    del data[0]
                    del data[0]
                    data_value = 'shot'
            except:
                pass
            return [
                    {
                        'label': 'Select structure',
                        'type': 'enumerator',
                        'value': data_value,
                        'name': 'structure_type',
                        'data': data
                    }, {
                        'label': 'Padding count',
                        'type': 'number',
                        'name': 'padding_count',
                        'value': 4
                    }, {
                        'label': 'Number of tasks',
                        'type': 'number',
                        'name': 'number_of_tasks',
                        'value': 2
                    }
                ]

    def launch(self, session, entities, event):
        '''Callback method for action.'''
        selection = event['data'].get('selection', [])
        values = event['data'].get('values', {})
        if values:
            if 'number_of_tasks' in values:
                form = get_form(
                    int(values['number_of_tasks']),
                    values['structure_type'],
                    entity_name + '_',
                    int(values['padding_count'])
                )
                return form

            else:
                structure = generate_structure(values)
                logging.info('Creating structure "{0}"'.format(str(structure)))
                create(entity, structure)
                return {
                    'success': True,
                    'message': 'Action completed successfully'
                }


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = BatchCreate(session)
    action_handler.register()


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
