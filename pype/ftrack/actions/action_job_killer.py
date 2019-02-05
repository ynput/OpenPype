# :coding: utf-8
# :copyright: Copyright (c) 2017 ftrack
import sys
import argparse
import logging

import ftrack_api
from pype.ftrack import BaseAction


class JobKiller(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'job.killer'
    #: Action label.
    label = 'Job Killer'
    #: Action description.
    description = 'Killing all running jobs younger than day'

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def interface(self, session, entities, event):
        if not event['data'].get('values', {}):
            title = 'Select jobs to kill'

            jobs = session.query(
                'select id, status from Job'
                ' where status in ("queued", "running")'
            )

            items = []
            import json
            for job in jobs:
                data = json.loads(job['data'])
                user = job['user']['username']
                created = job['created_at'].strftime('%d.%m.%Y %H:%M:%S')
                label = '{}/ {}/ {}'.format(
                    data['description'], created, user
                )
                item = {
                    'label': label,
                    'name': job['id'],
                    'type': 'boolean',
                    'value': False
                }
                items.append(item)

            return {
                'items': items,
                'title': title
            }

    def launch(self, session, entities, event):
        """ GET JOB """
        if 'values' not in event['data']:
            return

        values = event['data']['values']
        if len(values) <= 0:
            return {
                'success': True,
                'message': 'No jobs to kill!'
            }
        jobs = []
        job_ids = []

        for k, v in values.items():
            if v is True:
                job_ids.append(k)

        for id in job_ids:
            query = 'Job where id is "{}"'.format(id)
            jobs.append(session.query(query).one())
        # Update all the queried jobs, setting the status to failed.
        for job in jobs:
            try:
                job['status'] = 'failed'
                session.commit()
                self.log.debug((
                    'Changing Job ({}) status: {} -> failed'
                ).format(job['id'], job['status']))
            except Exception:
                self.warning.debug((
                    'Changing Job ({}) has failed'
                ).format(job['id']))

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
