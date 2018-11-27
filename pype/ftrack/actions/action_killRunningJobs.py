# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging

import datetime
import ftrack_api
from ftrack_action_handler import BaseAction


class JobKiller(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'job.kill'
    #: Action label.
    label = 'Job Killer'
    #: Action description.
    description = 'Killing all running jobs younger than day'


    def discover(self, session, entities, event):
        ''' Validation '''

        return True


    def launch(self, session, entities, event):
        """ GET JOB """

        yesterday = datetime.date.today() - datetime.timedelta(days=1)

        jobs = session.query(
            'select id, status from Job '
            'where status in ("queued", "running") and created_at > {0}'.format(yesterday)
        )

        # Update all the queried jobs, setting the status to failed.
        for job in jobs:
            self.log.debug(job['created_at'])
            self.log.debug('Changing Job ({}) status: {} -> failed'.format(job['id'], job['status']))
            job['status'] = 'failed'

        try:
            session.commit()
        except:
            session.rollback()

        self.log.info('All running jobs were killed Successfully!')
        return {
            'success': True,
            'message': 'All running jobs were killed Successfully!'
        }


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

    session = ftrack_api.Session()

    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
