..
    :copyright: Copyright (c) 2014 ftrack

.. _locations/configuring:

*********************
Configuring locations
*********************

To allow management of data by a location or retrieval of filesystem paths where
supported, a location instance needs to be configured in a session with an
:term:`accessor` and :term:`structure`.

.. note::

    The standard builtin locations require no further setup or configuration
    and it is not necessary to read the rest of this section to use them.

Before continuing, make sure that you are familiar with the general concepts
of locations by reading the :ref:`locations/overview`.

.. _locations/configuring/manually:

Configuring manually
====================

Locations can be configured manually when using a session by retrieving the
location and setting the appropriate attributes::

    location = session.query('Location where name is "my.location"').one()
    location.structure = ftrack_api.structure.id.IdStructure()
    location.priority = 50

.. _locations/configuring/automatically:

Configuring automatically
=========================

Often the configuration of locations should be determined by developers
looking after the core pipeline and so ftrack provides a way for a plugin to
be registered to configure the necessary locations for each session. This can
then be managed centrally if desired.

The configuration is handled through the standard events system via a topic
*ftrack.api.session.configure-location*. Set up an :ref:`event listener plugin
<understanding_sessions/plugins>` as normal with a register function that
accepts a :class:`~ftrack_api.session.Session` instance. Then register a
callback against the relevant topic to configure locations at the appropriate
time::

    import ftrack_api
    import ftrack_api.entity.location
    import ftrack_api.accessor.disk
    import ftrack_api.structure.id


    def configure_locations(event):
        '''Configure locations for session.'''
        session = event['data']['session']

        # Find location(s) and customise instances.
        location = session.query('Location where name is "my.location"').one()
        ftrack_api.mixin(location, ftrack_api.entity.location.UnmanagedLocationMixin)
        location.accessor = ftrack_api.accessor.disk.DiskAccessor(prefix='')
        location.structure = ftrack_api.structure.id.IdStructure()
        location.priority = 50


    def register(session):
        '''Register plugin with *session*.'''
        session.event_hub.subscribe(
            'topic=ftrack.api.session.configure-location',
            configure_locations
        )

.. note::

    If you expect the plugin to also be evaluated by the legacy API, remember
    to :ref:`validate the arguments <ftrack:release/migration/3.0.29/developer_notes/register_function>`.

So long as the directory containing the plugin exists on your
:envvar:`FTRACK_EVENT_PLUGIN_PATH`, the plugin will run for each session
created and any configured locations will then remain configured for the
duration of that related session.

Be aware that you can configure many locations in one plugin or have separate
plugins for different locations - the choice is entirely up to you!
