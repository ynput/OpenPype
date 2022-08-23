..
    :copyright: Copyright (c) 2015 ftrack

.. _release/migrating_from_old_api:

**********************
Migrating from old API
**********************

.. currentmodule:: ftrack_api.session

Why a new API?
==============

With the introduction of Workflows, ftrack is capable of supporting a greater
diversity of industries. We're enabling teams to closely align the system with
their existing practices and naming conventions, resulting in a tool that feels
more natural and intuitive. The old API was locked to specific workflows, making
it impractical to support this new feature naturally.

We also wanted this new flexibility to extend to developers, so we set about
redesigning the API to fully leverage the power in the system. And while we had
the wrenches out, we figured why not go that extra mile and build in some of the
features that we see developers having to continually implement in-house across
different companies - features such as caching and support for custom pipeline
extensions. In essence, we decided to build the API that, as pipeline
developers, we had always wanted from our production tracking and asset
management systems. We think we succeeded, and we hope you agree.

Installing
==========

Before, you used to download the API package from your ftrack instance. With 
each release of the new API we make it available on :term:`PyPi`, and 
installing is super simple:

.. code-block:: none

    pip install ftrack-python-api

Before installing, it is always good to check the latest
:ref:`release/release_notes`  to see which version of the ftrack server is
required.

.. seealso:: :ref:`installing`

Overview
========

An API needs to be approachable, so we built the new API to feel
intuitive and familiar. We bundle all the core functionality into one place – a
session – with consistent methods for interacting with entities in the system::

    import ftrack_api
    session = ftrack_api.Session()

The session is responsible for loading plugins and communicating with the ftrack
server and allows you to use multiple simultaneous sessions. You will no longer
need to explicitly call :meth:`ftrack.setup` to load plugins.

The core methods are straightforward:

Session.create
    create a new entity, like a new version.
Session.query
    fetch entities from the server using a powerful query language.
Session.delete
    delete existing entities.
Session.commit
    commit all changes in one efficient call.

.. note::

    The new API batches create, update and delete operations by default for
    efficiency. To synchronise local changes with the server you need to call
    :meth:`Session.commit`.

In addition all entities in the API now act like simple Python dictionaries,
with some additional helper methods where appropriate. If you know a little
Python (or even if you don't) getting up to speed should be a breeze::

    >>> print user.keys()
    ['first_name', 'last_name', 'email', ...]
    >>> print user['email']
    'old@example.com'
    >>> user['email'] = 'new@example.com'

And of course, relationships between entities are reflected in a natural way as
well::

    new_timelog = session.create('Timelog', {...})
    task['timelogs'].append(new_timelog)

.. seealso :: :ref:`tutorial`

The new API also makes use of caching in order to provide more efficient
retrieval of data by reducing the number of calls to the remote server.

.. seealso:: :ref:`caching`

Open source and standard code style
===================================

The new API is open source software and developed in public at
`Bitbucket <https://bitbucket.org/ftrack/ftrack-python-api>`_. We welcome you
to join us in the development and create pull requests there.

In the new API, we also follow the standard code style for Python,
:term:`PEP-8`. This means that you will now find that methods and variables are
written using  ``snake_case`` instead of ``camelCase``, amongst other things.

Package name
============

The new package is named :mod:`ftrack_api`. By using a new package name, we
enable you to use the old API and the new side-by-side in the same process.

Old API::

    import ftrack

New API::

    import ftrack_api

Specifying your credentials
===========================

The old API used three environment variables to authenticate with your ftrack
instance. While these continue to work as before, you now also have
the option to specify them when initializing the session::

    >>> import ftrack_api
    >>> session = ftrack_api.Session(
    ...     server_url='https://mycompany.ftrackapp.com',
    ...     api_key='7545384e-a653-11e1-a82c-f22c11dd25eq',
    ...     api_user='martin'
    ... )

In the examples below, will assume that you have imported the package and
created a session.

.. seealso:: 

    * :ref:`environment_variables`
    * :ref:`tutorial`


Querying objects
================

The old API relied on predefined methods for querying objects and constructors
which enabled you to get an entity by it's id or name.

Old API::

    project = ftrack.getProject('dev_tutorial')
    task = ftrack.Task('8923b7b3-4bf0-11e5-8811-3c0754289fd3')
    user = ftrack.User('jane')

New API::

    project = session.query('Project where name is "dev_tutorial"').one()
    task = session.get('Task', '8923b7b3-4bf0-11e5-8811-3c0754289fd3')
    user = session.query('User where username is "jane"').one()

While the new API can be a bit more verbose for simple queries, it is much more
powerful and allows you to filter on any field and preload related data::

    tasks = session.query(
        'select name, parent.name from Task '
        'where project.full_name is "My Project" '
        'and status.type.short is "DONE" '
        'and not timelogs any ()'
    ).all()

The above fetches all tasks for “My Project” that are done but have no timelogs.
It also pre-fetches related information about the tasks parent – all in one
efficient query.

.. seealso:: :ref:`querying`

Creating objects
================

In the old API, you create objects using specialized methods, such as 
:meth:`ftrack.createProject`, :meth:`Project.createSequence` and
:meth:`Task.createShot`.

In the new API, you can create any object using :meth:`Session.create`. In
addition, there are a few helper methods to reduce the amount of boilerplate
necessary to create certain objects. Don't forget to call :meth:`Session.commit`
once you have issued your create statements to commit your changes.

As an example, let's look at populating a project with a few entities.

Old API::

    project = ftrack.getProject('migration_test')

    # Get default task type and status from project schema
    taskType = project.getTaskTypes()[0]
    taskStatus = project.getTaskStatuses(taskType)[0]

    sequence = project.createSequence('001')

    # Create five shots with one task each
    for shot_number in xrange(10, 60, 10):
        shot = sequence.createShot(
            '{0:03d}'.format(shot_number)
        )
        shot.createTask(
            'Task name',
            taskType,
            taskStatus
        )


New API::

    project = session.query('Project where name is "migration_test"').one()

    # Get default task type and status from project schema
    project_schema = project['project_schema']
    default_shot_status = project_schema.get_statuses('Shot')[0]
    default_task_type = project_schema.get_types('Task')[0]
    default_task_status = project_schema.get_statuses(
        'Task', default_task_type['id']
    )[0]

    # Create sequence
    sequence = session.create('Sequence', {
        'name': '001',
        'parent': project
    })

    # Create five shots with one task each
    for shot_number in xrange(10, 60, 10):
        shot = session.create('Shot', {
            'name': '{0:03d}'.format(shot_number),
            'parent': sequence,
            'status': default_shot_status
        })
        session.create('Task', {
            'name': 'Task name',
            'parent': shot,
            'status': default_task_status,
            'type': default_task_type
        })

    # Commit all changes to the server.
    session.commit()

If you test the example above, one thing you might notice is that the new API
is much more efficient. Thanks to the transaction-based architecture in the new
API only a single call to the server is required to create all the objects.

.. seealso:: :ref:`working_with_entities/creating`

Updating objects
================

Updating objects in the new API works in a similar way to the old API. Instead
of using the :meth:`set` method on objects, you simply set the key of the 
entity to the new value, and call :meth:`Session.commit` to persist the
changes to the database.

The following example adjusts the duration and comment of a timelog for a
user using the old and new API, respectively.

Old API::

    import ftrack

    user = ftrack.User('john')
    user.set('email', 'john@example.com')

New API::

    import ftrack_api
    session = ftrack_api.Session()

    user = session.query('User where username is "john"').one()
    user['email'] = 'john@example.com'
    session.commit()

.. seealso:: :ref:`working_with_entities/updating`


Date and datetime attributes
============================

In the old API, date and datetime attributes where represented using a standard
:mod:`datetime` object. In the new API we have opted to use the :term:`arrow` 
library instead. Datetime attributes are represented in the server timezone,
but with the timezone information stripped.

Old API::

    >>> import datetime

    >>> task_old_api = ftrack.Task(task_id)
    >>> task_old_api.get('startdate')
    datetime.datetime(2015, 9, 2, 0, 0)

    >>> # Updating a datetime attribute
    >>> task_old_api.set('startdate', datetime.date.today())

New API::

    >>> import arrow

    >>> task_new_api = session.get('Task', task_id)
    >>> task_new_api['start_date']
    <Arrow [2015-09-02T00:00:00+00:00]>

    >>> # In the new API, utilize the arrow library when updating a datetime.
    >>> task_new_api['start_date'] = arrow.utcnow().floor('day')
    >>> session.commit()

Custom attributes
=================

In the old API, custom attributes could be retrieved from an entity by using
the methods :meth:`get` and :meth:`set`, like standard attributes. In the new 
API, custom attributes can be written and read from entities using the 
``custom_attributes`` property, which provides a dictionary-like interface.

Old API::

    >>> task_old_api = ftrack.Task(task_id)
    >>> task_old_api.get('my_custom_attribute')

    >>> task_old_api.set('my_custom_attribute', 'My new value')


New API::

    >>> task_new_api = session.get('Task', task_id)
    >>> task_new_api['custom_attributes']['my_custom_attribute']


    >>> task_new_api['custom_attributes']['my_custom_attribute'] = 'My new value'

For more information on working with custom attributes and existing
limitations, please see:

.. seealso::

    :ref:`example/custom_attribute`


Using both APIs side-by-side
============================

With so many powerful new features and the necessary support for more flexible
workflows, we chose early on to not limit the new API design by necessitating
backwards compatibility. However, we also didn't want to force teams using the
existing API to make a costly all-or-nothing switchover. As such, we have made
the new API capable of coexisting in the same process as the old API::

    import ftrack
    import ftrack_api

In addition, the old API will continue to be supported for some time, but do
note that it will not support the new `Workflows
<https://www.ftrack.com/workflows>`_ and will not have new features back ported
to it.

In the first example, we obtain a task reference using the old API and
then use the new API to assign a user to it::

    import ftrack
    import ftrack_api

    # Create session for new API, authenticating using envvars.
    session = ftrack_api.Session()

    # Obtain task id using old API
    shot = ftrack.getShot(['migration_test', '001', '010'])
    task = shot.getTasks()[0]
    task_id = task.getId()

    user = session.query(
        'User where username is "{0}"'.format(session.api_user)
    ).one()
    session.create('Appointment', {
        'resource': user,
        'context_id': task_id,
        'type': 'assignment'
    })

The second example fetches a version using the new API and uploads and sets a
thumbnail using the old API::

    import arrow
    import ftrack

    # fetch a version published today
    version = session.query(
        'AssetVersion where date >= "{0}"'.format(
            arrow.now().floor('day')
        )
    ).first()

    # Create a thumbnail using the old api.
    thumbnail_path = '/path/to/thumbnail.jpg'
    version_old_api = ftrack.AssetVersion(version['id'])
    thumbnail = version_old_api.createThumbnail(thumbnail_path)

    # Also set the same thumbnail on the task linked to the version.
    task_old_api = ftrack.Task(version['task_id'])
    task_old_api.setThumbnail(thumbnail)

.. note::

    It is now possible to set thumbnails using the new API as well, for more
    info see :ref:`example/thumbnail`.

Plugin registration
-------------------

To make event and location plugin register functions work with both old and new
API the function should be updated to validate the input arguments. For old
plugins the register method should validate that the first input is of type
``ftrack.Registry``, and for the new API it should be of type 
:class:`ftrack_api.session.Session`.

If the input parameter is not validated, a plugin might be mistakenly
registered twice, since both the new and old API will look for plugins the
same directories.

.. seealso::

    :ref:`ftrack:release/migration/3.0.29/developer_notes/register_function`


Example: publishing a new version
=================================

In the following example, we look at migrating a script which publishes a new
version with two components.

Old API::

    # Query a shot and a task to create the asset against.
    shot = ftrack.getShot(['dev_tutorial', '001', '010'])
    task = shot.getTasks()[0]

    # Create new asset.
    asset = shot.createAsset(name='forest', assetType='geo')

    # Create a new version for the asset.
    version = asset.createVersion(
        comment='Added more leaves.',
        taskid=task.getId()
    )

    # Get the calculated version number.
    print version.getVersion()

    # Add some components.
    previewPath = '/path/to/forest_preview.mov'
    previewComponent = version.createComponent(path=previewPath)

    modelPath = '/path/to/forest_mode.ma'
    modelComponent = version.createComponent(name='model', path=modelPath)

    # Publish.
    asset.publish()

    # Add thumbnail to version.
    thumbnail = version.createThumbnail('/path/to/forest_thumbnail.jpg')

    # Set thumbnail on other objects without duplicating it.
    task.setThumbnail(thumbnail)

New API::

    # Query a shot and a task to create the asset against.
    shot = session.query(
        'Shot where project.name is "dev_tutorial" '
        'and parent.name is "001" and name is "010"'
    ).one()
    task = shot['children'][0]

    # Create new asset.
    asset_type = session.query('AssetType where short is "geo"').first()
    asset = session.create('Asset', {
        'parent': shot,
        'name': 'forest',
        'type': asset_type
    })

    # Create a new version for the asset.
    status = session.query('Status where name is "Pending"').one()
    version = session.create('AssetVersion', {
        'asset': asset,
        'status': status,
        'comment': 'Added more leaves.',
        'task': task
    })

    # In the new API, the version number is not set until we persist the changes
    print 'Version number before commit: {0}'.format(version['version'])
    session.commit()
    print 'Version number after commit: {0}'.format(version['version'])

    # Add some components.
    preview_path = '/path/to/forest_preview.mov'
    preview_component = version.create_component(preview_path, location='auto')

    model_path = '/path/to/forest_mode.ma'
    model_component = version.create_component(model_path, {
        'name': 'model'
    }, location='auto')

    # Publish. Newly created version defaults to being published in the new api,
    # but if set to false you can update it by setting the key on the version.
    version['is_published'] = True

    # Persist the changes 
    session.commit()

    # Add thumbnail to version.
    thumbnail = version.create_thumbnail(
        '/path/to/forest_thumbnail.jpg'
    )

    # Set thumbnail on other objects without duplicating it.
    task['thumbnail'] = thumbnail
    session.commit()


Workarounds for missing convenience methods
===========================================

Query object by path
--------------------

In the old API, there existed a convenience methods to get an object by 
referencing the path (i.e object and parent names).

Old API::

    shot = ftrack.getShot(['dev_tutorial', '001', '010'])

New API::

    shot = session.query(
        'Shot where project.name is "dev_tutorial" '
        'and parent.name is "001" and name is "010"'
    )


Retrieving an object's parents
------------------------------

To retrieve a list of an object's parents, you could call the method
:meth:`getParents` in the old API. Currently, it is not possible to fetch this
in a single call using the new API, so you will have to traverse the ancestors 
one-by-one and fetch each object's parent.

Old API::

    parents = task.getParents()

New API::

    parents = []
    for item in task['link'][:-1]:
        parents.append(session.get(item['type'], item['id']))

Note that link includes the task itself so `[:-1]` is used to only retreive the
parents. To learn more about the `link` attribute, see
:ref:`Using link attributes example<example/link_attribute>`.

Limitations in the current version of the API
=============================================

The new API is still quite young and in active development and there are a few
limitations currently to keep in mind when using it.

Missing schemas
---------------

The following entities are as of the time of writing not currently available
in the new API. Let us know if you depend on any of them.

    * Booking
    * Calendar and Calendar Type
    * Dependency
    * Manager and Manager Type
    * Phase
    * Role
    * Task template
    * Temp data

Action base class
-----------------
There is currently no helper class for creating actions using the new API. We
will add one in the near future.

In the meantime, it is still possible to create actions without the base class
by listening and responding to the 
:ref:`ftrack:developing/events/list/ftrack.action.discover` and 
:ref:`ftrack:developing/events/list/ftrack.action.launch` events.

Legacy location
---------------

The ftrack legacy disk locations utilizing the 
:class:`InternalResourceIdentifierTransformer` has been deprecated.
