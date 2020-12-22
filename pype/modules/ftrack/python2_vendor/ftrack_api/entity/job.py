# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.entity.base


class Job(ftrack_api.entity.base.Entity):
    '''Represent job.'''

    def __init__(self, session, data=None, reconstructing=False):
        '''Initialise entity.

        *session* is an instance of :class:`ftrack_api.session.Session` that
        this entity instance is bound to.

        *data* is a mapping of key, value pairs to apply as initial attribute
        values.

        To set a job `description` visible in the web interface, *data* can
        contain a key called `data` which should be a JSON serialised
        dictionary containing description::

            data = {
                'status': 'running',
                'data': json.dumps(dict(description='My job description.')),
                ...
            }

        Will raise a :py:exc:`ValueError` if *data* contains `type` and `type`
        is set to something not equal to "api_job".

        *reconstructing* indicates whether this entity is being reconstructed,
        such as from a query, and therefore should not have any special creation
        logic applied, such as initialising defaults for missing data.

        '''

        if not reconstructing:
            if data.get('type') not in ('api_job', None):
                raise ValueError(
                    'Invalid job type "{0}". Must be "api_job"'.format(
                        data.get('type')
                    )
                )

        super(Job, self).__init__(
            session, data=data, reconstructing=reconstructing
        )
