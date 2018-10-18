# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging
import collections
import os
import datetime
import json
import ftrack_api
from ftrack_action_handler.action import BaseAction

from avalon import io, inventory, schema
from avalon.vendor import toml


class JobKiller(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'job.kill'

    #: Action label.
    label = 'Job Killer'

    #: Action description.
    description = 'Killing all running jobs younger than day'

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
        """ JOB SETTING """

        yesterday = datetime.date.today() - datetime.timedelta(days=1)

        jobs = session.query(
            'select id, status from Job '
            'where status in ("queued", "running") and created_at > {0}'.format(yesterday)
        )

        # Update all the queried jobs, setting the status to failed.
        for job in jobs:
            print(job['created_at'])
            print('Changing Job ({}) status: {} -> failed'.format(job['id'], job['status']))
            job['status'] = 'failed'

        session.commit()

        print('Complete')
        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an old or incompatible API and
    # return without doing anything.
    if not isinstance(session, ftrack_api.session.Session):
        return

    action_handler = JobKiller(session)
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
