..
    :copyright: Copyright (c) 2017 ftrack

.. _example/manage_custom_attribute_configuration:

****************************************
Managing custom attribute configurations
****************************************

From the API it is not only possible to
:ref:`read and update custom attributes for entities <example/custom_attribute>`,
but also managing custom attribute configurations.

Existing custom attribute configurations can be queried as ::

    # Print all existing custom attribute configurations.
    print session.query('CustomAttributeConfiguration').all()

Use :meth:`Session.create` to create a new custom attribute configuration::

    # Get the custom attribute type.
    custom_attribute_type = session.query(
        'CustomAttributeType where name is "text"'
    ).one()

    # Create a custom attribute configuration.
    session.create('CustomAttributeConfiguration', {
        'entity_type': 'assetversion',
        'type': custom_attribute_type,
        'label': 'Asset version text attribute',
        'key': 'asset_version_text_attribute',
        'default': 'bar',
        'config': json.dumps({'markdown': False})
    })

    # Persist it to the ftrack instance.
    session.commit()

.. tip::

    The example above does not add security roles. This can be done either
    from System Settings in the ftrack web application, or by following the
    :ref:`example/manage_custom_attribute_configuration/security_roles` example.

Global or project specific
==========================

A custom attribute can be global or project specific depending on the
`project_id` attribute::

    # Create a custom attribute configuration.
    session.create('CustomAttributeConfiguration', {
        # Set the `project_id` and the custom attribute will only be available
        # on `my_project`.
        'project_id': my_project['id'],
        'entity_type': 'assetversion',
        'type': custom_attribute_type,
        'label': 'Asset version text attribute',
        'key': 'asset_version_text_attribute',
        'default': 'bar',
        'config': json.dumps({'markdown': False})
    })
    session.commit()

A project specific custom attribute can be changed to a global::

    custom_attribute_configuration['project_id'] = None
    session.commit()

Changing a global custom attribute configuration to a project specific is not
allowed.

Entity types
============

Custom attribute configuration entity types are using a legacy notation. A
configuration can have one of the following as `entity_type`:

:task:
    Represents TypedContext (Folder, Shot, Sequence, Task, etc.) custom
    attribute configurations. When setting this as entity_type the
    object_type_id must be set as well.

    Creating a text custom attribute for Folder::

        custom_attribute_type = session.query(
            'CustomAttributeType where name is "text"'
        ).one()
        object_type = session.query('ObjectType where name is "Folder"').one()
        session.create('CustomAttributeConfiguration', {
            'entity_type': 'task',
            'object_type_id': object_type['id'],
            'type': custom_attribute_type,
            'label': 'Foo',
            'key': 'foo',
            'default': 'bar',
        })
        session.commit()

    Can be associated with a `project_id`.

:show:
    Represents Projects custom attribute configurations.

    Can be associated with a `project_id`.

:assetversion:
    Represents AssetVersion custom attribute configurations.

    Can be associated with a `project_id`.

:user:
    Represents User custom attribute configurations.

    Must be `global` and cannot be associated with a `project_id`.

:list:
    Represents List custom attribute configurations.

    Can be associated with a `project_id`.

:asset:
    Represents Asset custom attribute configurations.

    .. note::
       
        Asset custom attributes have limited support in the ftrack web
        interface.

    Can be associated with a `project_id`.

It is not possible to change type after a custom attribute configuration has
been created.

Custom attribute configuration types
====================================

Custom attributes can be of different data types depending on what type is set
in the configuration. Some types requires an extra json encoded config to be
set:

:text:
    A sting type custom attribute.

    The `default` value must be either :py:class:`str` or :py:class:`unicode`.

    Can be either presented as raw text or markdown formatted in applicaitons
    which support it. This is configured through a markwdown key::

        # Get the custom attribute type.
        custom_attribute_type = session.query(
            'CustomAttributeType where name is "text"'
        ).one()

        # Create a custom attribute configuration.
        session.create('CustomAttributeConfiguration', {
            'entity_type': 'assetversion',
            'type': custom_attribute_type,
            'label': 'Asset version text attribute',
            'key': 'asset_version_text_attribute',
            'default': 'bar',
            'config': json.dumps({'markdown': False})
        })

        # Persist it to the ftrack instance.
        session.commit()

:boolean:

    A boolean type custom attribute.

    The `default` value must be a :py:class:`bool`.

    No config is required.

:date:
    A date type custom attribute.

    The `default` value must be an :term:`arrow` date - e.g.
    arrow.Arrow(2017, 2, 8).

    No config is required.

:enumerator:
    An enumerator type custom attribute.

    The `default` value must be a list with either :py:class:`str` or
    :py:class:`unicode`.

    The enumerator can either be single or multi select. The config must a json
    dump of a dictionary containing `multiSelect` and `data`. Where
    `multiSelect` is True or False and data is a list of options. Each option
    should be a dictionary containing `value` and `menu`, where `menu` is meant
    to be used as label in a user interface.

    Create a custom attribute enumerator::

        custom_attribute_type = session.query(
            'CustomAttributeType where name is "enumerator"'
        ).first()
        session.create('CustomAttributeConfiguration', {
            'entity_type': 'assetversion',
            'type': custom_attribute_type,
            'label': 'Enumerator attribute',
            'key': 'enumerator_attribute',
            'default': ['bar'],
            'config': json.dumps({
                'multiSelect': True,
                'data': json.dumps([
                    {'menu': 'Foo', 'value': 'foo'},
                    {'menu': 'Bar', 'value': 'bar'}
                ])
            })
        })
        session.commit()

:dynamic enumerator:

    An enumerator type where available options are fetched from remote. Created
    in the same way as enumerator but without `data`.

:number:

    A number custom attribute can be either decimal or integer for presentation.

    This can be configured through the `isdecimal` config option::

        custom_attribute_type = session.query(
            'CustomAttributeType where name is "number"'
        ).first()
        session.create('CustomAttributeConfiguration', {
            'entity_type': 'assetversion',
            'type': custom_attribute_type,
            'label': 'Number attribute',
            'key': 'number_attribute',
            'default': 42,
            'config': json.dumps({
                'isdecimal': True
            })
        })
        session.commit()

Changing default
================

It is possible to update the `default` value of a custom attribute
configuration. This will not change the value of any existing custom
attributes::

    # Change the default value of custom attributes. This will only affect
    # newly created entities.
    custom_attribute_configuration['default'] = 43
    session.commit()

.. _example/manage_custom_attribute_configuration/security_roles:

Security roles
==============

By default new custom attribute configurations and the entity values are not
readable or writable by any security role.

This can be configured through the `read_security_roles` and `write_security_roles`
attributes::

    # Pick random security role.
    security_role = session.query('SecurityRole').first()
    custom_attribute_type = session.query(
        'CustomAttributeType where name is "date"'
    ).first()
    session.create('CustomAttributeConfiguration', {
        'entity_type': 'assetversion',
        'type': custom_attribute_type,
        'label': 'Date attribute',
        'key': 'date_attribute',
        'default': arrow.Arrow(2017, 2, 8),
        'write_security_roles': [security_role],
        'read_security_roles': [security_role]
    })
    session.commit()

.. note::

    Setting the correct security role is important and must be changed to
    whatever security role is appropriate for your configuration and intended
    purpose.

Custom attribute groups
=======================

A custom attribute configuration can be categorized using a
`CustomAttributeGroup`::

    group = session.query('CustomAttributeGroup').first()
    security_role = session.query('SecurityRole').first()
    custom_attribute_type = session.query(
        'CustomAttributeType where name is "enumerator"'
    ).first()
    session.create('CustomAttributeConfiguration', {
        'entity_type': 'assetversion',
        'type': custom_attribute_type,
        'label': 'Enumerator attribute',
        'key': 'enumerator_attribute',
        'default': ['bar'],
        'config': json.dumps({
            'multiSelect': True,
            'data': json.dumps([
                {'menu': 'Foo', 'value': 'foo'},
                {'menu': 'Bar', 'value': 'bar'}
            ])
        }),
        'group': group,
        'write_security_roles': [security_role],
        'read_security_roles': [security_role]
    })
    session.commit()

.. seealso::

    :ref:`example/custom_attribute`
