..
    :copyright: Copyright (c) 2015 ftrack

.. _release/migration:

***************
Migration notes
***************

.. note::

    Migrating from the old ftrack API? Read the dedicated :ref:`guide
    <release/migrating_from_old_api>`.

Migrate to upcoming 2.0.0
=========================

.. _release/migration/2.0.0/event_hub:

Default behavior for connecting to event hub
--------------------------------------------

The default behavior for the `ftrack_api.Session` class will change
for the argument `auto_connect_event_hub`, the default value will
switch from True to False. In order for code relying on the event hub
to continue functioning as expected you must modify your code
to explicitly set the argument to True or that you manually call
`session.event_hub.connect()`.

.. note::
    If you rely on the `ftrack.location.component-added` or
    `ftrack.location.component-removed` events to further process created
    or deleted components remember that your session must be connected
    to the event hub for the events to be published.


Migrate to 1.0.3
================

.. _release/migration/1.0.3/mutating_dictionary:

Mutating custom attribute dictionary
------------------------------------

Custom attributes can no longer be set by mutating entire dictionary::

    # This will result in an error.
    task['custom_attributes'] = dict(foo='baz', bar=2)
    session.commit()

Instead the individual values should be changed::

    # This works better.
    task['custom_attributes']['foo'] = 'baz'
    task['custom_attributes']['bar'] = 2
    session.commit()

Migrate to 1.0.0
================

.. _release/migration/1.0.0/chunked_transfer:

Chunked accessor transfers
--------------------------

Data transfers between accessors is now buffered using smaller chunks instead of
all data at the same time. Included accessor file representations such as
:class:`ftrack_api.data.File` and :class:`ftrack_api.accessor.server.ServerFile`
are built to handle that. If you have written your own accessor and file
representation you may have to update it to support multiple reads using the
limit parameter and multiple writes.

Migrate to 0.2.0
================

.. _release/migration/0.2.0/new_api_name:

New API name
------------

In this release the API has been renamed from `ftrack` to `ftrack_api`. This is
to allow both the old and new API to co-exist in the same environment without
confusion.

As such, any scripts using this new API need to be updated to import
`ftrack_api` instead of `ftrack`. For example:

**Previously**::

    import ftrack
    import ftrack.formatter
    ...

**Now**::

    import ftrack_api
    import ftrack_api.formatter
    ...
