..
    :copyright: Copyright (c) 2014 ftrack

.. _example/job:

*************
Managing jobs
*************

.. currentmodule:: ftrack_api.session

Jobs can be used to display feedback to users in the ftrack web interface when
performing long running tasks in the API.

To create a job use :meth:`Session.create`::

    user = # Get a user from ftrack.

    job = session.create('Job', {
        'user': user,
        'status': 'running'
    })

The created job will appear as running in the :guilabel:`jobs` menu for the
specified user. To set a description on the job, add a dictionary containing
description as the `data` key:

.. note::

    In the current version of the API the dictionary needs to be JSON
    serialised.

.. code-block:: python
    
    import json

    job = session.create('Job', {
        'user': user,
        'status': 'running',
        'data': json.dumps({
            'description': 'My custom job description.'
        })
    })

When the long running task has finished simply set the job as completed and
continue with the next task.

.. code-block:: python

    job['status'] = 'done'
    session.commit()

Attachments
===========

Job attachments are files that are attached to a job. In the ftrack web
interface these attachments can be downloaded by clicking on a job in the `Jobs`
menu.

To get a job's attachments through the API you can use the `job_components`
relation and then use the ftrack server location to get the download URL::

    server_location = session.query(
        'Location where name is "ftrack.server"'
    ).one()

    for job_component in job['job_components']:
        print 'Download URL: {0}'.format(
            server_location.get_url(job_component['component'])   
        )

To add an attachment to a job you have to add it to the ftrack server location
and create a `jobComponent`::

    server_location = session.query(
        'Location where name is "ftrack.server"'
    ).one()    

    # Create component and name it "My file".
    component = session.create_component(
        '/path/to/file',
        data={'name': 'My file'},
        location=server_location
    )

    # Attach the component to the job.
    session.create(
        'JobComponent',
        {'component_id': component['id'], 'job_id': job['id']}
    )

    session.commit()

.. note::

    The ftrack web interface does only support downloading one attachment so
    attaching more than one will have limited support in the web interface.
