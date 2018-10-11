# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack

import sys
import argparse
import logging

import ftrack_api

from ftrack_action_handler.action import BaseAction


class SyncToAvalon(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'update.anim.bid'

    #: Action label.
    label = 'Sync to Avalon'

    #: Action description.
    description = 'Send data from Ftrack to Avalon'

    def validate_selection(self, session, entities):
        '''Return if *entities* is a valid selection.'''
        # if (len(entities) != 1):
        #     # If entities contains more than one item return early since
        #     # metadata cannot be edited for several entites at the same time.
        #     return False
        pass
        # entity_type, entity_id = entities[0]
        # if (
        #     entity_type not in session.types
        # ):
        #     # Return False if the target entity does not have a metadata
        #     # attribute.
        #     return False

        return True

    def discover(self, session, entities, event):
        '''Return True if action is valid.'''

        self.logger.info('Got selection: {0}'.format(entities))
        return self.validate_selection(session, entities)

    def launch(self, session, entities, event):
        '''Launch edit meta data action.'''

        for entity in entities:

            entity_type, entity_id = entity
            entity = session.get(entity_type, entity_id)

            # copy_attrs = ['difficulty', 'fend', 'fstart', 'handles', 'chars']

            # collect all parents from the task
            # parent = session.get(entity['link'][-2]['type'], entity['link'][-2]['id'])
            # project = session.get(entity['link'][0]['type'], entity['link'][0]['id'])

            # attrs = parent['custom_attributes']
            #fend = int(attrs['fend'])
            #fstart = int(attrs['fstart'])
            print(entity['link'])
            # entity['custom_attributes']['anim_cost'] = au * anim_rate

        # try:
        #     session.commit()
        # except:
        #     # Commit failed, rollback session and re-raise.
        #     session.rollback()
        #     raise

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = SyncToAvalon(session)
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

    session = ftrack_api.Session(
        server_url="https://pype.ftrackapp.com",
        api_key="4e01eda0-24b3-4451-8e01-70edc03286be",
        api_user="jakub.trllo"
    )
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
