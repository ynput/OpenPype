..
    :copyright: Copyright (c) 2014 ftrack

.. _example/scope:

************
Using scopes
************

.. currentmodule:: ftrack_api.session

Entities can be queried based on their scopes::

    >>> tasks = session.query(
    ...     'Task where scopes.name is "London"'
    ... )

Scopes can be read and modified for entities::

    >>> scope = session.query(
    ...     'Scope where name is "London"'
    ... )[0]
    ...
    ... if scope in task['scopes']:
    ...     task['scopes'].remove(scope)
    ... else:
    ...     task['scopes'].append(scope)
