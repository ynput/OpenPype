..
    :copyright: Copyright (c) 2016 ftrack

.. currentmodule:: ftrack_api.session

.. _example/publishing:

*******************
Publishing versions
*******************

To know more about publishing and the concepts around publishing, read the
`ftrack article <http://ftrack.rtd.ftrack.com/en/stable/developing/publishing/index.html>`_
about publishing.

To publish an asset you first need to get the context where the asset should be
published::

    # Get a task from a given id.
    task = session.get('Task', '423ac382-e61d-4802-8914-dce20c92b740')

And the parent of the task which will be used to publish the asset on::

    asset_parent = task['parent']

Then we create an asset and a version on the asset::

    asset_type = session.query('AssetType where name is "Geometry"').one()
    asset = session.create('Asset', {
        'name': 'My asset',
        'type': asset_type,
        'parent': asset_parent
    })
    asset_version = session.create('AssetVersion', {
        'asset': asset,
        'task': task
    })

.. note::

    The task is not used as the parent of the asset, instead the task is linked
    directly to the AssetVersion.

Then when we have a version where we can create the components::

    asset_version.create_component(
        '/path/to/a/file.mov', location='auto'
    )
    asset_version.create_component(
        '/path/to/a/another-file.mov', location='auto'
    )

    session.commit()

This will automatically create a new component and add it to the location which
has been configured as the first in priority.

Components can also be named and added to a custom location like this::

    location = session.query('Location where name is "my-location"')
    asset_version.create_component(
        '/path/to/a/file.mov',
        data={
            'name': 'foobar'
        },
        location=location
    )

.. seealso::

    * :ref:`example/component`
    * :ref:`example/web_review`
    * :ref:`example/thumbnail`
