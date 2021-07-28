..
    :copyright: Copyright (c) 2016 ftrack

.. currentmodule:: ftrack_api.session

.. _example/web_review:

*************************
Publishing for web review
*************************

Follow the :ref:`example/encode_media` example if you want to
upload and encode media using ftrack.

If you already have a file encoded in the correct format and want to bypass
the built-in encoding in ftrack, you can create the component manually
and add it to the `ftrack.server` location::

    # Retrieve or create version.
    version = session.query('AssetVersion', 'SOME-ID')

    server_location = session.query('Location where name is "ftrack.server"').one()
    filepath = '/path/to/local/file.mp4'

    component = version.create_component(
        path=filepath,
        data={
            'name': 'ftrackreview-mp4'
        },
        location=server_location
    )

    # Meta data needs to contain *frameIn*, *frameOut* and *frameRate*.
    component['metadata']['ftr_meta'] = json.dumps({
        'frameIn': 0,
        'frameOut': 150,
        'frameRate': 25
    })

    component.session.commit()

To publish an image for review the steps are similar::

    # Retrieve or create version.
    version = session.query('AssetVersion', 'SOME-ID')

    server_location = session.query('Location where name is "ftrack.server"').one()
    filepath = '/path/to/image.jpg'

    component = version.create_component(
        path=filepath,
        data={
            'name': 'ftrackreview-image'
        },
        location=server_location
    )

    # Meta data needs to contain *format*.
    component['metadata']['ftr_meta'] = json.dumps({
        'format': 'image'
    })

    component.session.commit()

Here is a list of components names and how they should be used:

==================  =====================================
Component name      Use
==================  =====================================
ftrackreview-image  Images reviewable in the browser
ftrackreview-mp4    H.264/mp4 video reviewable in browser
ftrackreview-webm   WebM video reviewable in browser
==================  =====================================

.. note::

    Make sure to use the pre-defined component names and set the `ftr_meta` on
    the components or review will not work.
