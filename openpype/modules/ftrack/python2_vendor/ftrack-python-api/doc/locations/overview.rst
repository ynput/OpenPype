..
    :copyright: Copyright (c) 2014 ftrack

.. _locations/overview:

********
Overview
********

Locations provides a way to easily track and manage data (files, image sequences
etc.) using ftrack.

With locations it is possible to see where published data is in the world and
also to transfer data automatically between different locations, even different
storage mechanisms, by defining a few simple :term:`Python` plugins. By keeping
track of the size of the data it also helps manage storage capacity better. In
addition, the intrinsic links to production information makes assigning work to
others and transferring only the relevant data much simpler as well as greatly
reducing the burden on those responsible for archiving finished work.

Concepts
========

The system is implemented in layers using a few key concepts in order to provide
a balance between out of the box functionality and custom configuration.

.. _locations/overview/locations:

Locations
---------

Data locations can be varied in scope and meaning - a facility, a laptop, a
specific drive. As such, rather than place a hard limit on what can be
considered a location, ftrack simply requires that a location be identifiable by
a string and that string be unique to that location.

A global company with facilities in many different parts of the world might
follow a location naming convention similar to the following:

    * 'ftrack.london.server01'
    * 'ftrack.london.server02'
    * 'ftrack.nyc.server01'
    * 'ftrack.amsterdam.server01'
    * '<company>.<city>.<server#>'

Whereas, for a looser setup, the following might suit better:

    * 'bjorns-workstation'
    * 'fredriks-mobile'
    * 'martins-laptop'
    * 'cloud-backup'

Availability
------------

When tracking data across several locations it is important to be able to
quickly find out where data is available and where it is not. As such, ftrack
provides simple mechanisms for retrieving information on the availability of a
:term:`component` in each location.

For a single file, the availability with be either 0% or 100%. For containers,
such as file sequences, each file is tracked separately and the availability of
the container calculated as an overall percentage (e.g. 47%).

.. _locations/overview/accessors:

Accessors
---------

Due to the flexibility of what can be considered a location, the system must be
able to cope with locations that represent different ways of storing data. For
example, data might be stored on a local hard drive, a cloud service or even in
a database.

In addition, the method of accessing that storage can change depending on
perspective - local filesystem, FTP, S3 API etc.

To handle this, ftrack introduces the idea of an :term:`accessor` that provides
access to the data in a standard way. An accessor is implemented in
:term:`Python` following a set interface and can be configured at runtime to
provide relevant access to a location.

With an accessor configured for a location, it becomes possible to not only
track data, but also manage it through ftrack by using the accessor to add and
remove data from the location.

At present, ftrack includes a :py:class:`disk accessor
<ftrack_api.accessor.disk.DiskAccessor>` for local filesystem access. More will be
added over time and developers are encouraged to contribute their own.

.. _locations/overview/structure:

Structure
---------

Another important consideration for locations is how data should be structured
in the location (folder structure and naming conventions). For example,
different facilities may want to use different folder structures, or different
storage mechanisms may use different paths for the data.

For this, ftrack supports the use of a :term:`Python` structure plugin. This
plugin is called when adding a :term:`component` to a location in order to
determine the correct structure to use.

.. note::

    A structure plugin accepts an ftrack entity as its input and so can be
    reused for generating general structures as well. For example, an action
    callback could be implemented to create the base folder structure for some
    selected shots by reusing a structure plugin.

.. _locations/overview/resource_identifiers:

Resource identifiers
--------------------

When a :term:`component` can be linked to multiple locations it becomes
necessary to store information about the relationship on the link rather than
directly on the :term:`component` itself. The most important information is the
path to the data in that location.

However, as seen above, not all locations may be filesystem based or accessed
using standard filesystem protocols. For this reason, and to help avoid
confusion, this *path* is referred to as a :term:`resource identifier` and no
limitations are placed on the format. Keep in mind though that accessors use
this information (retrieved from the database) in order to work out how to
access the data, so the format used must be compatible with all the accessors
used for any one location. For this reason, most
:term:`resource identifiers <resource identifier>` should ideally look like
relative filesystem paths.

.. _locations/overview/resource_identifiers/transformer:

Transformer
^^^^^^^^^^^

To further support custom formats for
:term:`resource identifiers <resource identifier>`, it is also possible to
configure a resource identifier transformer plugin which will convert
the identifiers before they are stored centrally and after they are retrieved.

A possible use case of this might be to store JSON encoded metadata about a path
in the database and convert this to an actual filesystem path on retrieval.
