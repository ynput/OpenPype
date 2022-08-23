..
    :copyright: Copyright (c) 2014 ftrack

.. _understanding_sessions:

**********************
Understanding sessions
**********************

.. currentmodule:: ftrack_api.session

All communication with an ftrack server takes place through a :class:`Session`.
This allows more opportunity for configuring the connection, plugins etc. and
also makes it possible to connect to multiple ftrack servers from within the
same Python process.

.. _understanding_sessions/connection:

Connection
==========

A session can be manually configured at runtime to connect to a server with
certain credentials::

    >>> session = ftrack_api.Session(
    ...     server_url='https://mycompany.ftrackapp.com',
    ...     api_key='7545384e-a653-11e1-a82c-f22c11dd25eq',
    ...     api_user='martin'
    ... )

Alternatively, a session can use the following environment variables to
configure itself:

    * :envvar:`FTRACK_SERVER`
    * :envvar:`FTRACK_API_USER`
    * :envvar:`FTRACK_API_KEY`

When using environment variables, no server connection arguments need to be
passed manually::

    >>> session = ftrack_api.Session()

.. _understanding_sessions/unit_of_work:

Unit of work
============

Each session follows the unit of work pattern. This means that many of the
operations performed using a session will happen locally and only be persisted
to the server at certain times, notably when calling :meth:`Session.commit`.
This approach helps optimise calls to the server and also group related logic
together in a transaction::

    user = session.create('User', {})
    user['username'] = 'martin'
    other_user = session.create('User', {'username': 'bjorn'})
    other_user['email'] = 'bjorn@example.com'

Behind the scenes a series of :class:`operations
<ftrack_api.operation.Operation>` are recorded reflecting the changes made. You
can take a peek at these operations if desired by examining the
``Session.recorded_operations`` property::

    >>> for operation in session.recorded_operations:
    ...     print operation
    <ftrack_api.operation.CreateEntityOperation object at 0x0000000003EC49B0>
    <ftrack_api.operation.UpdateEntityOperation object at 0x0000000003E16898>
    <ftrack_api.operation.CreateEntityOperation object at 0x0000000003E16240>
    <ftrack_api.operation.UpdateEntityOperation object at 0x0000000003E16128>

Calling :meth:`Session.commit` persists all recorded operations to the server
and clears the operation log::

    session.commit()

.. note::

    The commit call will optimise operations to be as efficient as possible
    without breaking logical ordering. For example, a create followed by updates
    on the same entity will be compressed into a single create.

Queries are special and always issued on demand. As a result, a query may return
unexpected results if the relevant local changes have not yet been sent to the
server::

    >>> user = session.create('User', {'username': 'some_unique_username'})
    >>> query = 'User where username is "{0}"'.format(user['username'])
    >>> print len(session.query(query))
    0
    >>> session.commit()
    >>> print len(session.query(query))
    1

Where possible, query results are merged in with existing data transparently
with any local changes preserved::

    >>> user = session.query('User').first()
    >>> user['email'] = 'me@example.com'  # Not yet committed to server.
    >>> retrieved = session.query(
    ...     'User where id is "{0}"'.format(user['id'])
    ... ).one()
    >>> print retrieved['email']  # Displays locally set value.
    'me@example.com'
    >>> print retrieved is user
    True

This is possible due to the smart :ref:`caching` layer in the session.

.. _understanding_sessions/auto_population:

Auto-population
===============

Another important concept in a session is that of auto-population. By default a
session is configured to auto-populate missing attribute values on access. This
means that the first time you access an attribute on an entity instance a query
will be sent to the server to fetch the value::

    user = session.query('User').first()
    # The next command will issue a request to the server to fetch the
    # 'username' value on demand at this is the first time it is accessed.
    print user['username']

Once a value has been retrieved it is :ref:`cached <caching>` locally in the
session and accessing it again will not issue more server calls::

    # On second access no server call is made.
    print user['username']

You can control the auto population behaviour of a session by either changing
the ``Session.auto_populate`` attribute on a session or using the provided
context helper :meth:`Session.auto_populating` to temporarily change the
setting. When turned off you may see a special
:attr:`~ftrack_api.symbol.NOT_SET` symbol that represents a value has not yet
been fetched::

    >>> with session.auto_populating(False):
    ...     print user['email']
    NOT_SET

Whilst convenient for simple scripts, making many requests to the server for
each attribute can slow execution of a script. To support optimisation the API
includes methods for batch fetching attributes. Read about them in
:ref:`querying/projections` and :ref:`working_with_entities/populating`.

.. _understanding_sessions/entity_types:

Entity types
============

When a session has successfully connected to the server it will automatically
download schema information and :ref:`create appropriate classes
<working_with_entities/entity_types>` for use. This is important as different
servers can support different entity types and configurations.

This information is readily available and useful if you need to check that the
entity types you expect are present. Here's how to print a list of all entity
types registered for use in the current API session::

    >>> print session.types.keys()
    [u'Task', u'Shot', u'TypedContext', u'Sequence', u'Priority',
     u'Status', u'Project', u'User', u'Type', u'ObjectType']

Each entity type is backed by a :ref:`customisable class
<working_with_entities/entity_types>` that further describes the entity type and
the attributes that are available.

.. hint::

    If you need to use an :func:`isinstance` check, always go through the
    session as the classes are built dynamically::

        >>> isinstance(entity, session.types['Project'])

.. _understanding_sessions/plugins:

Configuring plugins
===================

Plugins are used by the API to extend it with new functionality, such as 
:term:`locations <location>` or adding convenience methods to
:ref:`understanding_sessions/entity_types`. In addition to new API
functionality, event plugins may also be used for event processing by listening
to :ref:`ftrack update events <handling_events>` or adding custom functionality to ftrack by registering
:term:`actions <action>`.


When starting a new :class:`Session` either pass the *plugins_paths* to search
explicitly or rely on the environment variable 
:envvar:`FTRACK_EVENT_PLUGIN_PATH`. As each session is independent of others,
you can configure plugins per session.

The paths will be searched for :term:`plugins <plugin>`, python files
which expose a `register` function. These functions will be evaluated and can
be used extend the API with new functionality, such as locations or actions.

If you do not specify any override then the session will attempt to discover and
use the default plugins.

Plugins are discovered using :func:`ftrack_api.plugin.discover` with the
session instance passed as the sole positional argument. Most plugins should
take the form of a mount function that then subscribes to specific :ref:`events
<handling_events>` on the session::

    def configure_locations(event):
        '''Configure locations for session.'''
        session = event['data']['session']
        # Find location(s) and customise instances.

    def register(session):
        '''Register plugin with *session*.'''
        session.event_hub.subscribe(
            'topic=ftrack.api.session.configure-location',
            configure_locations
        )

Additional keyword arguments can be passed as *plugin_arguments* to the
:class:`Session` on instantiation. These are passed to the plugin register
function if its signature supports them::

    # a_plugin.py
    def register(session, reticulate_splines=False):
        '''Register plugin with *session*.'''
        ...

    # main.py
    session = ftrack_api.Session(
        plugin_arguments={
            'reticulate_splines': True,
            'some_other_argument': 42
        }
    )

.. seealso::

    Lists of events which you can subscribe to in your plugins are available
    both for :ref:`synchronous event published by the python API <event_list>`
    and :ref:`asynchronous events published by the server <ftrack:developing/events/list>`


Quick setup
-----------

1. Create a directory where plugins will be stored. Place any plugins you want
loaded automatically in an API *session* here.

.. image:: /image/configuring_plugins_directory.png

2. Configure the :envvar:`FTRACK_EVENT_PLUGIN_PATH` to point to the directory.


Detailed setup
--------------

Start out by creating a directory on your machine where you will store your
plugins. Download :download:`example_plugin.py </resource/example_plugin.py>`
and place it in the directory.

Open up a terminal window, and ensure that plugin is picked up when
instantiating the session and manually setting the *plugin_paths*::

    >>>  # Set up basic logging
    >>> import logging
    >>> logging.basicConfig()
    >>> plugin_logger = logging.getLogger('com.example.example-plugin')
    >>> plugin_logger.setLevel(logging.DEBUG)
    >>>
    >>> # Configure the API, loading plugins in the specified paths.
    >>> import ftrack_api
    >>> plugin_paths = ['/path/to/plugins']
    >>> session = ftrack_api.Session(plugin_paths=plugin_paths)

If everything is working as expected, you should see the following in the
output::

    DEBUG:com.example.example-plugin:Plugin registered

Instead of specifying the plugin paths when instantiating the session, you can
also specify the :envvar:`FTRACK_EVENT_PLUGIN_PATH` to point to the directory.
To specify multiple directories, use the path separator for your operating
system.