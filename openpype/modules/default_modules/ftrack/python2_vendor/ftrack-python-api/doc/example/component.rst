..
    :copyright: Copyright (c) 2014 ftrack

.. _example/component:

***********************
Working with components
***********************

.. currentmodule:: ftrack_api.session

Components can be created manually or using the provide helper methods on a
:meth:`session <ftrack_api.session.Session.create_component>` or existing
:meth:`asset version
<ftrack_api.entity.asset_version.AssetVersion.create_component>`::

    component = version.create_component('/path/to/file_or_sequence.jpg')
    session.commit()

When a component is created using the helpers it is automatically added to a
location.

.. seealso:: :ref:`Locations tutorial <locations/tutorial>`
