import sys
import argparse
import logging
import os
import getpass

import ftrack_api
from ftrack_action_handler import BaseAction



class ClientReviewSort(BaseAction):
    '''Custom action.'''

    #: Action identifier.
    identifier = 'client.review.sort'

    #: Action label.
    label = 'Sort Review'


    def validateSelection(self, entities):
        '''Return true if the selection is valid. '''

        if len(entities) == 0:
            return False

        return True


    def discover(self, session, entities, event):
        '''Return action config if triggered on a single selection.'''

        selection = event['data']['selection']
        # this action will only handle a single version.
        if (not self.validateSelection(entities) or
            selection[0]['entityType'] != 'reviewsession'):
            return False

        return True


    def launch(self, session, entities, event):

        entity_type, entity_id = entities[0]
        entity = session.get(entity_type, entity_id)

        # Get all objects from Review Session and all 'sort order' possibilities
        obj_list = []
        sort_order_list = []
        for obj in entity['review_session_objects']:
            obj_list.append(obj)
            sort_order_list.append(obj['sort_order'])

        # Sort criteria
        obj_list = sorted(obj_list, key=lambda k: k['asset_version']['task']['name'])
        obj_list = sorted(obj_list, key=lambda k: k['version'])
        obj_list = sorted(obj_list, key=lambda k: k['name'])

        # Set 'sort order' to sorted list, so they are sorted in Ftrack also
        for i in range(len(obj_list)):
            obj_list[i]['sort_order'] = sort_order_list[i]

        session.commit()

        return {
            'success': True,
            'message': 'Client Review sorted!'
        }


def register(session, **kw):
    '''Register action. Called when used as an event plugin.'''
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = ClientReviewSort(session)
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
