..
    :copyright: Copyright (c) 2014 ftrack

.. _tutorial:

********
Tutorial
********

.. currentmodule:: ftrack_api.session

This tutorial provides a quick dive into using the API and the broad stroke
concepts involved.

First make sure the ftrack Python API is :ref:`installed <installing>`.

Then start a Python session and import the ftrack API::

    >>> import ftrack_api

The API uses :ref:`sessions <understanding_sessions>` to manage communication
with an ftrack server. Create a session that connects to your ftrack server
(changing the passed values as appropriate)::

    >>> session = ftrack_api.Session(
    ...     server_url='https://mycompany.ftrackapp.com',
    ...     api_key='7545384e-a653-11e1-a82c-f22c11dd25eq',
    ...     api_user='martin'
    ... )

.. note::

    A session can use :ref:`environment variables
    <understanding_sessions/connection>` to configure itself.

Now print a list of the available entity types retrieved from the server::

    >>> print session.types.keys()
    [u'TypedContext', u'ObjectType', u'Priority', u'Project', u'Sequence',
     u'Shot', u'Task', u'Status', u'Type', u'Timelog', u'User']

Now the list of possible entity types is known, :ref:`query <querying>` the
server to retrieve entities of a particular type by using the
:meth:`Session.query` method::

    >>> projects = session.query('Project')

Each project retrieved will be an :ref:`entity <working_with_entities>` instance
that behaves much like a standard Python dictionary. For example, to find out
the available keys for an entity, call the
:meth:`~ftrack_api.entity.Entity.keys` method::

    >>> print projects[0].keys()
    [u'status', u'is_global', u'name', u'end_date', u'context_type',
     u'id', u'full_name', u'root', u'start_date']

Now, iterate over the retrieved entities and print each ones name::

    >>> for project in projects:
    ...     print project['name']
    test
    client_review
    tdb
    man_test
    ftrack
    bunny

.. note::

    Many attributes for retrieved entities are loaded on demand when the
    attribute is first accessed. Doing this lots of times in a script can be
    inefficient, so it is worth using :ref:`projections <querying/projections>`
    in queries or :ref:`pre-populating <working_with_entities/populating>`
    entities where appropriate. You can also :ref:`customise default projections
    <working_with_entities/entity_types/default_projections>` to help others
    pre-load common attributes.

To narrow a search, add :ref:`criteria <querying/criteria>` to the query::

    >>> active_projects = session.query('Project where status is active')

Combine criteria for more powerful queries::

    >>> import arrow
    >>>
    >>> active_projects_ending_before_next_week = session.query(
    ...     'Project where status is active and end_date before "{0}"'
    ...     .format(arrow.now().replace(weeks=+1))
    ... )

Some attributes on an entity will refer to another entity or collection of
entities, such as *children* on a *Project* being a collection of *Context*
entities that have the project as their parent::

    >>> project = session.query('Project').first()
    >>> print project['children']
    <ftrack_api.collection.Collection object at 0x00000000045B1438>

And on each *Context* there is a corresponding *parent* attribute which is a
link back to the parent::

    >>> child = project['children'][0]
    >>> print child['parent'] is project
    True

These relationships can also be used in the criteria for a query::

    >>> results = session.query(
    ...     'Context where parent.name like "te%"'
    ... )

To create new entities in the system use :meth:`Session.create`::

    >>> new_sequence = session.create('Sequence', {
    ...     'name': 'Starlord Reveal'
    ... })

The created entity is not yet persisted to the server, but it is still possible
to modify it.

    >>> new_sequence['description'] = 'First hero character reveal.'

The sequence also needs a parent. This can be done in one of two ways:

* Set the parent attribute on the sequence::

    >>> new_sequence['parent'] = project

* Add the sequence to a parent's children attribute::

    >>> project['children'].append(new_sequence)

When ready, persist to the server using :meth:`Session.commit`::

    >>> session.commit()

When finished with a :class:`Session`, it is important to :meth:`~Session.close`
it in order to release resources and properly unsubscribe any registered event
listeners. It is also possible to use the session as a context manager in order
to have it closed automatically after use::

    >>> with ftrack_api.Session() as session:
    ...     print session.query('User').first()
    <User(0154901c-eaf9-11e5-b165-00505681ec7a)>
    >>> print session.closed
    True

Once a :class:`Session` is closed, any operations that attempt to use the closed
connection to the ftrack server will fail::

    >>> session.query('Project').first()
    ConnectionClosedError: Connection closed.

Continue to the next section to start learning more about the API in greater
depth or jump over to the :ref:`usage examples <example>` if you prefer to learn
by example.
