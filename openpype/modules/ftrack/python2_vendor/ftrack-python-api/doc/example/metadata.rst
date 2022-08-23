..
    :copyright: Copyright (c) 2014 ftrack

.. _example/metadata:

**************
Using metadata
**************

.. currentmodule:: ftrack_api.session

Key/value metadata can be written to entities using the metadata property
and also used to query entities.

The metadata property has a similar interface as a dictionary and keys can be
printed using the keys method::

    >>> print new_sequence['metadata'].keys()
    ['frame_padding', 'focal_length']

or items::

    >>> print new_sequence['metadata'].items()
    [('frame_padding': '4'), ('focal_length': '70')]

Read existing metadata::

    >>> print new_sequence['metadata']['frame_padding']
    '4'

Setting metadata can be done in a few ways where that later one will replace
any existing metadata::

    new_sequence['metadata']['frame_padding'] = '5'
    new_sequence['metadata'] = {
        'frame_padding': '4'
    }

Entities can also be queried using metadata::

    session.query(
        'Sequence where metadata any (key is "frame_padding" and value is "4")'
    )
