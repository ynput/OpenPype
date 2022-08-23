..
    :copyright: Copyright (c) 2015 ftrack

.. currentmodule:: ftrack_api.session

.. _example:

**************
Usage examples
**************

The following examples show how to use the API to accomplish specific tasks
using the default configuration.

.. note::

    If you are using a server with a customised configuration you may need to
    alter the examples slightly to make them work correctly.

Most of the examples assume you have the *ftrack_api* package imported and have
already constructed a :class:`Session`::

    import ftrack_api

    session = ftrack_api.Session()


.. toctree::

    project
    component
    review_session
    metadata
    custom_attribute
    manage_custom_attribute_configuration
    link_attribute
    scope
    job
    note
    list
    timer
    assignments_and_allocations
    thumbnail
    encode_media
    entity_links
    web_review
    publishing
    security_roles
    task_template
    sync_ldap_users
    invite_user

