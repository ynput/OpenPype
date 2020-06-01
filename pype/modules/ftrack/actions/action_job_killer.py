import os
import sys
import argparse
import logging
import json

import ftrack_api
from pype.modules.ftrack import BaseAction


class JobKiller(BaseAction):
    '''Edit meta data action.'''

    #: Action identifier.
    identifier = 'job.killer'
    #: Action label.
    label = "Pype Admin"
    variant = '- Job Killer'
    #: Action description.
    description = 'Killing selected running jobs'
    #: roles that are allowed to register this action
    role_list = ['Pypeclub', 'Administrator']
    icon = '{}/ftrack/action_icons/PypeAdmin.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    def discover(self, session, entities, event):
        ''' Validation '''

        return True

    def interface(self, session, entities, event):
        if not event['data'].get('values', {}):
            title = 'Select jobs to kill'

            jobs = session.query(
                'select id, status from Job'
                ' where status in ("queued", "running")'
            ).all()

            items = []

            item_splitter = {'type': 'label', 'value': '---'}
            for job in jobs:
                try:
                    data = json.loads(job['data'])
                    desctiption = data['description']
                except Exception:
                    desctiption = '*No description*'
                user = job['user']['username']
                created = job['created_at'].strftime('%d.%m.%Y %H:%M:%S')
                label = '{} - {} - {}'.format(
                    desctiption, created, user
                )
                item_label = {
                    'type': 'label',
                    'value': label
                }
                item = {
                    'name': job['id'],
                    'type': 'boolean',
                    'value': False
                }
                if len(items) > 0:
                    items.append(item_splitter)
                items.append(item_label)
                items.append(item)

            if len(items) == 0:
                return {
                    'success': False,
                    'message': 'Didn\'t found any running jobs'
                }
            else:
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
                origin_status = job["status"]
                job['status'] = 'failed'
                session.commit()
                self.log.debug((
                    'Changing Job ({}) status: {} -> failed'
                ).format(job['id'], origin_status))
            except Exception:
                session.rollback()
                self.log.warning((
                    'Changing Job ({}) has failed'
                ).format(job['id']))

        self.log.info('All running jobs were killed Successfully!')
        return {
            'success': True,
            'message': 'All running jobs were killed Successfully!'
        }


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    JobKiller(session, plugins_presets).register()


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
