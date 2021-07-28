..
    :copyright: Copyright (c) 2014 ftrack

.. _locations/tutorial:

********
Tutorial
********

This tutorial is a walkthrough on how you interact with Locations using the 
ftrack :term:`API`. Before you read this tutorial, make sure you familiarize
yourself with the location concepts by reading the :ref:`locations/overview`.

All examples assume you are using Python 2.x, have the :mod:`ftrack_api`
module imported and a :class:`session <ftrack_api.session.Session>` created.

.. code-block:: python

    import ftrack_api
    session = ftrack_api.Session()

.. _locations/creating-locations:

Creating locations
==================

Locations can be created just like any other entity using
:meth:`Session.create <ftrack_api.session.Session.create>`::

    location = session.create('Location', dict(name='my.location'))
    session.commit()

.. note:: 
    Location names beginning with ``ftrack.`` are reserved for internal use. Do
    not use this prefix for your location names.

To create a location only if it doesn't already exist use the convenience 
method :meth:`Session.ensure <ftrack_api.session.Session.ensure>`. This will return
either an existing matching location or a newly created one.

Retrieving locations
====================

You can retrieve existing locations using the standard session
:meth:`~ftrack_api.session.Session.get` and
:meth:`~ftrack_api.session.Session.query` methods::

    # Retrieve location by unique id.
    location_by_id = session.get('Location', 'unique-id')

    # Retrieve location by name.
    location_by_name = session.query(
        'Location where name is "my.location"'
    ).one()

To retrieve all existing locations use a standard query::

    all_locations = session.query('Location').all()
    for existing_location in all_locations:
        print existing_location['name']

Configuring locations
=====================

At this point you have created a custom location "my.location" in the database
and have an instance to reflect that. However, the location cannot be used in
this session to manage  data unless it has been configured. To configure a
location for the session, set the appropriate attributes for accessor and
structure::

    import tempfile
    import ftrack_api.accessor.disk
    import ftrack_api.structure.id

    # Assign a disk accessor with *temporary* storage
    location.accessor = ftrack_api.accessor.disk.DiskAccessor(
        prefix=tempfile.mkdtemp()
    )

    # Assign using ID structure.
    location.structure = ftrack_api.structure.id.IdStructure()

    # Set a priority which will be used when automatically picking locations.
    # Lower number is higher priority.
    location.priority = 30

To learn more about how to configure locations automatically in a session, see
:ref:`locations/configuring`.

.. note::

    If a location is not configured in a session it can still be used as a
    standard entity and to find out availability of components

Using components with locations
===============================

The Locations :term:`API` tries to use sane defaults to stay out of your way.
When creating :term:`components <component>`, a location is automatically picked
using :meth:`Session.pick_location <ftrack_api.session.Session.pick_location>`::

    (_, component_path) = tempfile.mkstemp(suffix='.txt')
    component_a = session.create_component(path=component_path)

To override, specify a location explicitly::

    (_, component_path) = tempfile.mkstemp(suffix='.txt')
    component_b = session.create_component(
        path=component_path, location=location
    )

If you set the location to ``None``, the component will only be present in the
special origin location for the duration of the session::

    (_, component_path) = tempfile.mkstemp(suffix='.txt')
    component_c = session.create_component(path=component_path, location=None)

After creating a :term:`component` in a location, it can be added to another
location by calling :meth:`Location.add_component
<ftrack_api.entity.location.Location.add_component>` and passing the location to
use as the *source* location::

    origin_location = session.query(
        'Location where name is "ftrack.origin"'
    ).one()
    location.add_component(component_c, origin_location)

To remove a component from a location use :meth:`Location.remove_component
<ftrack_api.entity.location.Location.remove_component>`::

    location.remove_component(component_b)

Each location specifies whether to automatically manage data when adding or
removing components. To ensure that a location does not manage data, mixin the
relevant location mixin class before use::

    import ftrack_api
    import ftrack_api.entity.location

    ftrack_api.mixin(location, ftrack_api.entity.location.UnmanagedLocationMixin)

Accessing paths
===============

The locations system is designed to help avoid having to deal with filesystem
paths directly. This is particularly important when you consider that a number
of locations won't provide any direct filesystem access (such as cloud storage).

However, it is useful to still be able to get a filesystem path from locations
that support them (typically those configured with a
:class:`~ftrack_api.accessor.disk.DiskAccessor`). For example, you might need to
pass a filesystem path to another application or perform a copy using a faster
protocol.

To retrieve the path if available, use :meth:`Location.get_filesystem_path
<ftrack_api.entity.location.Location.get_filesystem_path>`::

    print location.get_filesystem_path(component_c)

Obtaining component availability
================================

Components in locations have a notion of availability. For regular components,
consisting of a single file, the availability would be either 0 if the 
component is unavailable or 100 percent if the component is available in the 
location. Composite components, like image sequences, have an availability 
which is proportional to the amount of child components that have been added to 
the location. 

For example, an image sequence might currently be in a state of being 
transferred to :data:`test.location`. If half of the images are transferred,  it
might be possible to start working with the sequence. To check availability use
the helper :meth:`Session.get_component_availability
<ftrack_api.session.Session.get_component_availability>` method::

    print session.get_component_availability(component_c)

There are also convenience methods on both :meth:`components
<ftrack_api.entity.component.Component.get_availability>` and :meth:`locations
<ftrack_api.entity.location.Location.get_component_availability>` for
retrieving availability as well::

    print component_c.get_availability()
    print location.get_component_availability(component_c)

Location events
===============

If you want to receive event notifications when components are added to or 
removed from locations, you can subscribe to the topics published,
:data:`ftrack_api.symbol.COMPONENT_ADDED_TO_LOCATION_TOPIC` or
:data:`ftrack_api.symbol.COMPONENT_REMOVED_FROM_LOCATION_TOPIC` and the callback
you want to be run.
