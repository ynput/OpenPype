..
    :copyright: Copyright (c) 2016 ftrack

.. _example/thumbnail:

***********************
Working with thumbnails
***********************

Components can be used as thumbnails on various entities, including
`Project`, `Task`, `AssetVersion` and `User`.  To create and set a thumbnail
you can use the helper method 
:meth:`~ftrack_api.entity.component.CreateThumbnailMixin.create_thumbnail` on
any entity that can have a thumbnail::

    task = session.get('Task', my_task_id)
    thumbnail_component = task.create_thumbnail('/path/to/image.jpg')

It is also possible to set an entity thumbnail by setting its `thumbnail`
relation or `thumbnail_id` attribute to a component you would
like to use as a thumbnail. For a component to be usable as a thumbnail,
it should

    1. Be a FileComponent.
    2. Exist in the *ftrack.server* :term:`location`.
    3. Be of an appropriate resolution and valid file type.

The following example creates a new component in the server location, and
uses that as a thumbnail for a task::

    task = session.get('Task', my_task_id)
    server_location = session.query(
        'Location where name is "ftrack.server"'
    ).one()

    thumbnail_component = session.create_component(
        '/path/to/image.jpg',
        dict(name='thumbnail'),
        location=server_location
    )
    task['thumbnail'] = thumbnail_component
    session.commit()

The next example reuses a version's thumbnail for the asset parent thumbnail::

    asset_version = session.get('AssetVersion', my_asset_version_id)
    asset_parent = asset_version['asset']['parent']
    asset_parent['thumbnail_id'] = asset_version['thumbnail_id']
    session.commit()

.. _example/thumbnail/url:

Retrieving thumbnail URL
========================

To get an URL to a thumbnail, `thumbnail_component`, which can be used used
to download or display the image in an interface, use the following::

    import ftrack_api.symbol
    server_location = session.get('Location', ftrack_api.symbol.SERVER_LOCATION_ID)
    thumbnail_url = server_location.get_thumbnail_url(thumbnail_component)
    thumbnail_url_tiny = server_location.get_thumbnail_url(
        thumbnail_component, size=100
    )
    thumbnail_url_large = server_location.get_thumbnail_url(
        thumbnail_component, size=500
    )

.. seealso::

    :ref:`example/component`
