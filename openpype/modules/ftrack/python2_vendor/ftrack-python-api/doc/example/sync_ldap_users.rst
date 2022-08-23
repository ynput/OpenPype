..
    :copyright: Copyright (c) 2014 ftrack

.. _example/sync_with_ldap:

********************
Sync users with LDAP
********************

.. currentmodule:: ftrack_api.session


If ftrack is configured to connect to LDAP you may trigger a
synchronization through the api using the
:meth:`ftrack_api.session.Session.call`::

    result = session.call([
        dict(
            action='delayed_job',
            job_type='SYNC_USERS_LDAP'
        )
    ])
    job = result[0]['data]

You will get a `ftrack_api.entity.job.Job` instance back which can be used
to check the success of the job::

    if job.get('status') == 'failed':
        # The job failed get the error.
        logging.error(job.get('data'))
