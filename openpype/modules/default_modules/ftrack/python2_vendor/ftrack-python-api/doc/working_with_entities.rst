..
    :copyright: Copyright (c) 2014 ftrack

.. _working_with_entities:

*********************
Working with entities
*********************

.. currentmodule:: ftrack_api.session

:class:`Entity <ftrack_api.entity.base.Entity>` instances are Python dict-like
objects whose keys correspond to attributes for that type in the system. They
may also provide helper methods to perform common operations such as replying to
a note::

    note = session.query('Note').first()
    print note.keys()
    print note['content']
    note['content'] = 'A different message!'
    reply = note.create_reply(...)

.. _working_with_entities/attributes:

Attributes
==========

Each entity instance is typed according to its underlying entity type on the
server and configured with appropriate attributes. For example, a *task* will be
represented by a *Task* class and have corresponding attributes. You can
:ref:`customise entity classes <working_with_entities/entity_types>` to alter
attribute access or provide your own helper methods.

To see the available attribute names on an entity use the
:meth:`~ftrack_api.entity.base.Entity.keys` method on the instance::

    >>> task = session.query('Task').first()
    >>> print task.keys()
    ['id', 'name', ...]

If you need more information about the type of attribute, examine the
``attributes`` property on the corresponding class::

    >>> for attribute in type(task).attributes:
    ...     print attribute
    <ftrack_api.attribute.ScalarAttribute(id) object at 66701296>
    <ftrack_api.attribute.ScalarAttribute(name) object at 66702192>
    <ftrack_api.attribute.ReferenceAttribute(status) object at 66701240>
    <ftrack_api.attribute.CollectionAttribute(timelogs) object at 66701184>
    <ftrack_api.attribute.KeyValueMappedCollectionAttribute(metadata) object at 66701632>
    ...

Notice that there are different types of attribute such as
:class:`~ftrack_api.attribute.ScalarAttribute` for plain values or
:class:`~ftrack_api.attribute.ReferenceAttribute` for relationships. These
different types are reflected in the behaviour on the entity instance when
accessing a particular attribute by key:

    >>> # Scalar
    >>> print task['name']
    'model'
    >>> task['name'] = 'comp'

    >>> # Single reference
    >>> print task['status']
    <Status(e610b180-4e64-11e1-a500-f23c91df25eb)>
    >>> new_status = session.query('Status').first()
    >>> task['status'] = new_status

    >>> # Collection
    >>> print task['timelogs']
    <ftrack_api.collection.Collection object at 0x00000000040D95C0>
    >>> print task['timelogs'][:]
    [<dynamic ftrack Timelog object 72322240>, ...]
    >>> new_timelog = session.create('Timelog', {...})
    >>> task['timelogs'].append(new_timelog)

.. _working_with_entities/attributes/bidirectional:

Bi-directional relationships
----------------------------

Some attributes refer to different sides of a bi-directional relationship. In
the current version of the API bi-directional updates are not propagated
automatically to the other side of the relationship. For example, setting a
*parent* will not update the parent entity's *children* collection locally.
There are plans to support this behaviour better in the future. For now, after
commit, :ref:`populate <working_with_entities/populating>` the reverse side
attribute manually.

.. _working_with_entities/creating:

Creating entities
=================

In order to create a new instance of an entity call :meth:`Session.create`
passing in the entity type to create and any initial attribute values::

    new_user = session.create('User', {'username': 'martin'})

If there are any default values that can be set client side then they will be
applied at this point. Typically this will be the unique entity key::

    >>> print new_user['id']
    170f02a4-6656-4f15-a5cb-c4dd77ce0540

At this point no information has been sent to the server. However, you are free
to continue :ref:`updating <working_with_entities/updating>` this object
locally until you are ready to persist the changes by calling
:meth:`Session.commit`.

If you are wondering about what would happen if you accessed an unset attribute
on a newly created entity, go ahead and give it a go::

    >>> print new_user['first_name']
    NOT_SET

The session knows that it is a newly created entity that has not yet been
persisted so it doesn't try to fetch any attributes on access even when
``session.auto_populate`` is turned on.

.. _working_with_entities/updating:

Updating entities
=================

Updating an entity is as simple as modifying the values for specific keys on
the dict-like instance and calling :meth:`Session.commit` when ready. The entity
to update can either be a new entity or a retrieved entity::

    task = session.query('Task').first()
    task['bid'] = 8

Remember that, for existing entities, accessing an attribute will load it from
the server automatically. If you are interested in just setting values without
first fetching them from the server, turn :ref:`auto-population
<understanding_sessions/auto_population>` off temporarily::

    >>> with session.auto_populating(False):
    ...    task = session.query('Task').first()
    ...    task['bid'] = 8


.. _working_with_entities/resetting:

Server side reset of entity attributes or settings.
===========================

Some entities support resetting of attributes, for example
to reset a users api key::


    session.reset_remote(
        'api_key', entity=session.query('User where username is "test_user"').one()
    )

.. note::
    Currently the only attribute possible to reset is 'api_key' on
    the user entity type.


.. _working_with_entities/deleting:

Deleting entities
=================

To delete an entity you need an instance of the entity in your session (either
from having created one or retrieving one). Then call :meth:`Session.delete` on
the entity and :meth:`Session.commit` when ready::

    task_to_delete = session.query('Task').first()
    session.delete(task_to_delete)
    ...
    session.commit()

.. note::

    Even though the entity is deleted, you will still have access to the local
    instance and any local data stored on that instance whilst that instance
    remains in memory.

Keep in mind that some deletions, when propagated to the server, will cause
other entities to be deleted also, so you don't have to worry about deleting an
entire hierarchy manually. For example, deleting a *Task* will also delete all
*Notes* on that task.

.. _working_with_entities/populating:

Populating entities
===================

When an entity is retrieved via :meth:`Session.query` or :meth:`Session.get` it
will have some attributes prepopulated. The rest are dynamically loaded when
they are accessed. If you need to access many attributes it can be more
efficient to request all those attributes be loaded in one go. One way to do
this is to use a :ref:`projections <querying/projections>` in queries.

However, if you have entities that have been passed to you from elsewhere you
don't have control over the query that was issued to get those entities. In this
case you can you can populate those entities in one go using
:meth:`Session.populate` which works exactly like :ref:`projections
<querying/projections>` in queries do, but operating against known entities::

    >>> users = session.query('User')
    >>> session.populate(users, 'first_name, last_name')
    >>> with session.auto_populating(False):  # Turn off for example purpose.
    ...     for user in users:
    ...         print 'Name: {0}'.format(user['first_name'])
    ...         print 'Email: {0}'.format(user['email'])
    Name: Martin
    Email: NOT_SET
    ...

.. note::

    You can populate a single or many entities in one call so long as they are
    all the same entity type.

.. _working_with_entities/entity_states:

Entity states
=============

Operations on entities are :ref:`recorded in the session
<understanding_sessions/unit_of_work>` as they happen. At any time you can
inspect an entity to determine its current state from those pending operations.

To do this, use :func:`ftrack_api.inspection.state`::

    >>> import ftrack_api.inspection
    >>> new_user = session.create('User', {})
    >>> print ftrack_api.inspection.state(new_user)
    CREATED
    >>> existing_user = session.query('User').first()
    >>> print ftrack_api.inspection.state(existing_user)
    NOT_SET
    >>> existing_user['email'] = 'martin@example.com'
    >>> print ftrack_api.inspection.state(existing_user)
    MODIFIED
    >>> session.delete(new_user)
    >>> print ftrack_api.inspection.state(new_user)
    DELETED

.. _working_with_entities/entity_types:

Customising entity types
========================

Each type of entity in the system is represented in the Python client by a
dedicated class. However, because the types of entities can vary these classes
are built on demand using schema information retrieved from the server.

Many of the default classes provide additional helper methods which are mixed
into the generated class at runtime when a session is started.

In some cases it can be useful to tailor the custom classes to your own pipeline
workflows. Perhaps you want to add more helper functions, change attribute
access rules or even providing a layer of backwards compatibility for existing
code. The Python client was built with this in mind and makes such
customisations as easy as possible.

When a :class:`Session` is constructed it fetches schema details from the
connected server and then calls an :class:`Entity factory
<ftrack_api.entity.factory.Factory>` to create classes from those schemas. It
does this by emitting a synchronous event,
*ftrack.api.session.construct-entity-type*, for  each schema and expecting a
*class* object to be returned.

In the default setup, a :download:`construct_entity_type.py
<../resource/plugin/construct_entity_type.py>` plugin is placed on the
:envvar:`FTRACK_EVENT_PLUGIN_PATH`. This plugin will register a trivial subclass
of :class:`ftrack_api.entity.factory.StandardFactory` to create the classes in
response to the construct event. The simplest way to get started is to edit this
default plugin as required.

.. seealso:: :ref:`understanding_sessions/plugins`

.. _working_with_entities/entity_types/default_projections:

Default projections
-------------------

When a :ref:`query <querying>` is issued without any :ref:`projections
<querying/projections>`, the session will automatically add default projections
according to the type of the entity.

For example, the following shows that for a *User*, only *id* is fetched by
default when no projections added to the query::

    >>> user = session.query('User').first()
    >>> with session.auto_populating(False):  # For demonstration purpose only.
    ...     print user.items()
    [
        (u'id', u'59f0963a-15e2-11e1-a5f1-0019bb4983d8')
        (u'username', Symbol(NOT_SET)),
        (u'first_name', Symbol(NOT_SET)),
        ...
    ]

.. note::

    These default projections are also used when you access a relationship
    attribute using the dictionary key syntax.

If you want to default to fetching *username* for a *Task* as well then you can
change the default_projections* in your class factory plugin::

    class Factory(ftrack_api.entity.factory.StandardFactory):
        '''Entity class factory.'''

        def create(self, schema, bases=None):
            '''Create and return entity class from *schema*.'''
            cls = super(Factory, self).create(schema, bases=bases)

            # Further customise cls before returning.
            if schema['id'] == 'User':
                cls.default_projections = ['id', 'username']

            return cls

Now a projection-less query will also query *username* by default:

.. note::

    You will need to start a new session to pick up the change you made::

        session = ftrack_api.Session()

.. code-block:: python

    >>> user = session.query('User').first()
    >>> with session.auto_populating(False):  # For demonstration purpose only.
    ...     print user.items()
    [
        (u'id', u'59f0963a-15e2-11e1-a5f1-0019bb4983d8')
        (u'username', u'martin'),
        (u'first_name', Symbol(NOT_SET)),
        ...
    ]

Note that if any specific projections are applied in a query, those override
the default projections entirely. This allows you to also *reduce* the data
loaded on demand::

    >>> session = ftrack_api.Session()  # Start new session to avoid cache.
    >>> user = session.query('select id from User').first()
    >>> with session.auto_populating(False):  # For demonstration purpose only.
    ...     print user.items()
    [
        (u'id', u'59f0963a-15e2-11e1-a5f1-0019bb4983d8')
        (u'username', Symbol(NOT_SET)),
        (u'first_name', Symbol(NOT_SET)),
        ...
    ]

.. _working_with_entities/entity_types/helper_methods:

Helper methods
--------------

If you want to add additional helper methods to the constructed classes to
better support your pipeline logic, then you can simply patch the created
classes in your factory, much like with changing the default projections::

    def get_full_name(self):
        '''Return full name for user.'''
        return '{0} {1}'.format(self['first_name'], self['last_name']).strip()

    class Factory(ftrack_api.entity.factory.StandardFactory):
        '''Entity class factory.'''

        def create(self, schema, bases=None):
            '''Create and return entity class from *schema*.'''
            cls = super(Factory, self).create(schema, bases=bases)

            # Further customise cls before returning.
            if schema['id'] == 'User':
                cls.get_full_name = get_full_name

            return cls

Now you have a new helper method *get_full_name* on your *User* entities::

    >>> session = ftrack_api.Session()  # New session to pick up changes.
    >>> user = session.query('User').first()
    >>> print user.get_full_name()
    Martin Pengelly-Phillips

If you'd rather not patch the existing classes, or perhaps have a lot of helpers
to mixin, you can instead inject your own class as the base class. The only
requirement is that it has the base :class:`~ftrack_api.entity.base.Entity`
class in its ancestor classes::

    import ftrack_api.entity.base


    class CustomUser(ftrack_api.entity.base.Entity):
        '''Represent user.'''

        def get_full_name(self):
            '''Return full name for user.'''
            return '{0} {1}'.format(self['first_name'], self['last_name']).strip()


    class Factory(ftrack_api.entity.factory.StandardFactory):
        '''Entity class factory.'''

        def create(self, schema, bases=None):
            '''Create and return entity class from *schema*.'''
            # Alter base class for constructed class.
            if bases is None:
                bases = [ftrack_api.entity.base.Entity]

            if schema['id'] == 'User':
                bases = [CustomUser]

            cls = super(Factory, self).create(schema, bases=bases)
            return cls

The resulting effect is the same::

    >>> session = ftrack_api.Session()  # New session to pick up changes.
    >>> user = session.query('User').first()
    >>> print user.get_full_name()
    Martin Pengelly-Phillips

.. note::

    Your custom class is not the leaf class which will still be a dynamically
    generated class. Instead your custom class becomes the base for the leaf
    class::

        >>> print type(user).__mro__
        (<dynamic ftrack class 'User'>, <dynamic ftrack class 'CustomUser'>, ...)
