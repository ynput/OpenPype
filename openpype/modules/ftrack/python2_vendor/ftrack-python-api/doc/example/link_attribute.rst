..
    :copyright: Copyright (c) 2015 ftrack

.. _example/link_attribute:

*********************
Using link attributes
*********************

The `link` attribute can be used to retreive the ids and names of the parents of
an object. It is particularly useful in cases where the path of an object must
be presented in a UI, but can also be used to speedup certain query patterns.

You can use the `link` attribute on any entity inheriting from a
`Context` or `AssetVersion`. Here we use it on the `Task` entity::

    task = session.query(
        'select link from Task where name is "myTask"'
    ).first()
    print task['link']

It can also be used create a list of parent entities, including the task
itself::

    entities = []
    for item in task['link']:
        entities.append(session.get(item['type'], item['id']))

The `link` attribute is an ordered list of dictionaries containting data
of the parents and the item itself. Each dictionary contains the following
entries:

    id
        The id of the object and can be used to do a :meth:`Session.get`.
    name
        The name of the object.
    type
        The schema id of the object.

A more advanced use-case is to get the parent names and ids of all timelogs for
a user::

    for timelog in session.query(
        'select context.link, start, duration from Timelog '
        'where user.username is "john.doe"'
    ):
        print timelog['context']['link'], timelog['start'], timelog['duration']

The attribute is also available from the `AssetVersion` asset relation::

    for asset_version in session.query(
        'select link from AssetVersion '
        'where user.username is "john.doe"'
    ):
        print asset_version['link']
