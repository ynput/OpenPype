..
    :copyright: Copyright (c) 2015 ftrack

.. _example/list:

***********
Using lists
***********

.. currentmodule:: ftrack_api.session

Lists can be used to create a collection of asset versions or objects such as
tasks. It could be a list of items that should be sent to client, be included in
todays review session or items that belong together in way that is different
from the project hierarchy.

There are two types of lists, one for asset versions and one for other objects
such as tasks.

To create a list use :meth:`Session.create`::

    user = # Get a user from ftrack.
    project = # Get a project from ftrack.
    list_category = # Get a list category from ftrack.

    asset_version_list = session.create('AssetVersionList', {
        'owner': user,
        'project': project,
        'category': list_category
    })

    task_list = session.create('TypedContextList', {
        'owner': user,
        'project': project,
        'category': list_category
    })

Then add items to the list like this::

    asset_version_list['items'].append(asset_version)
    task_list['items'].append(task)

And remove items from the list like this::

    asset_version_list['items'].remove(asset_version)
    task_list['items'].remove(task)
