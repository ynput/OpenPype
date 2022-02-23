..
    :copyright: Copyright (c) 2016 ftrack

.. _example/entity_links:

******************
Using entity links
******************

A link can be used to represent a dependency or another relation between
two entities in ftrack.

There are two types of entities that can be linked:

*   Versions can be linked to other asset versions, where the link entity type
    is `AssetVersionLink`.
*   Objects like Task, Shot or Folder, where the link entity type is
    `TypedContextLink`.

Both `AssetVersion` and `TypedContext` objects have the same relations
`incoming_links` and `outgoing_links`. To list the incoming links to a Shot we
can use the relationship `incoming_links`::

    for link in shot['incoming_links']:
        print link['from'], link['to']

In the above example `link['to']` is the shot and `link['from']` could be an
asset build or something else that is linked to the shot. There is an equivalent
`outgoing_links` that can be used to access outgoing links on an object.

To create a new link between objects or asset versions create a new 
`TypedContextLink` or `AssetVersionLink` entity with the from and to properties
set. In this example we will link two asset versions::

    session.create('AssetVersionLink', {
        'from': from_asset_version,
        'to': to_asset_version
    })
    session.commit()

Using asset version link shortcut
=================================

Links on asset version can also be created by the use of the `uses_versions` and
`used_in_versions` relations::

    rig_version['uses_versions'].append(model_version)
    session.commit()

This has the same result as creating the `AssetVersionLink` entity as in the
previous section.

Which versions are using the model can be listed with::

    for version in model_version['used_in_versions']:
        print '{0} is using {1}'.format(version, model_version)
