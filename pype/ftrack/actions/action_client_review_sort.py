import sys
import argparse
import logging

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction


class ClientReviewSort(BaseAction):
    '''Custom action.'''

    #: Action identifier.
    identifier = 'client.review.sort'

    #: Action label.
    label = 'Sort Review'

    def discover(self, session, entities, event):
        ''' Validation '''

        if (len(entities) == 0 or entities[0].entity_type != 'ReviewSession'):
            return False

        return True

    def launch(self, session, entities, event):

        entity = entities[0]

        # Get all objects from Review Session and all 'sort order' possibilities
        obj_list = []
        sort_order_list = []
        for obj in entity['review_session_objects']:
            obj_list.append(obj)
            sort_order_list.append(obj['sort_order'])

        # Sort criteria
        obj_list = sorted(obj_list, key=lambda k: k['version'])
        obj_list = sorted(
            obj_list, key=lambda k: k['asset_version']['task']['name']
        )
        obj_list = sorted(obj_list, key=lambda k: k['name'])

        # Set 'sort order' to sorted list, so they are sorted in Ftrack also
        for i in range(len(obj_list)):
            obj_list[i]['sort_order'] = sort_order_list[i]

        session.commit()

        return {
            'success': True,
            'message': 'Client Review sorted!'
        }


def register(session, plugins_presets={}):
    '''Register action. Called when used as an event plugin.'''

    ClientReviewSort(session, plugins_presets).register()


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
