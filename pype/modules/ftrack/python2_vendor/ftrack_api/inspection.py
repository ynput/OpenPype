# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

from builtins import str
from future.utils import native_str
import collections

import ftrack_api.symbol
import ftrack_api.operation


def identity(entity):
    '''Return unique identity of *entity*.'''
    return (
        str(entity.entity_type),
        list(primary_key(entity).values())
    )


def primary_key(entity):
    '''Return primary key of *entity* as an ordered mapping of {field: value}.

    To get just the primary key values::

        primary_key(entity).values()

    '''
    primary_key = collections.OrderedDict()
    for name in entity.primary_key_attributes:
        value = entity[name]
        if value is ftrack_api.symbol.NOT_SET:
            raise KeyError(
                'Missing required value for primary key attribute "{0}" on '
                'entity {1!r}.'.format(name, entity)
            )

        # todo: Compatiblity fix, review for better implementation.
        primary_key[native_str(name)] = native_str(value)

    return primary_key


def _state(operation, state):
    '''Return state following *operation* against current *state*.'''
    if (
        isinstance(
            operation, ftrack_api.operation.CreateEntityOperation
        )
        and state is ftrack_api.symbol.NOT_SET
    ):
        state = ftrack_api.symbol.CREATED

    elif (
        isinstance(
            operation, ftrack_api.operation.UpdateEntityOperation
        )
        and state is ftrack_api.symbol.NOT_SET
    ):
        state = ftrack_api.symbol.MODIFIED

    elif isinstance(
        operation, ftrack_api.operation.DeleteEntityOperation
    ):
        state = ftrack_api.symbol.DELETED

    return state


def state(entity):
    '''Return current *entity* state.

    .. seealso:: :func:`ftrack_api.inspection.states`.

    '''
    value = ftrack_api.symbol.NOT_SET

    for operation in entity.session.recorded_operations:
        # Determine if operation refers to an entity and whether that entity
        # is *entity*.
        if (
            isinstance(
                operation,
                (
                    ftrack_api.operation.CreateEntityOperation,
                    ftrack_api.operation.UpdateEntityOperation,
                    ftrack_api.operation.DeleteEntityOperation
                )
            )
            and operation.entity_type == entity.entity_type
            and operation.entity_key == primary_key(entity)
        ):
            value = _state(operation, value)

    return value


def states(entities):
    '''Return current states of *entities*.

    An optimised function for determining states of multiple entities in one
    go.

    .. note::

        All *entities* should belong to the same session.

    .. seealso:: :func:`ftrack_api.inspection.state`.

    '''
    if not entities:
        return []

    session = entities[0].session

    entities_by_identity = collections.OrderedDict()
    for entity in entities:
        key = (entity.entity_type, str(list(primary_key(entity).values())))
        entities_by_identity[key] = ftrack_api.symbol.NOT_SET

    for operation in session.recorded_operations:
        if (
            isinstance(
                operation,
                (
                    ftrack_api.operation.CreateEntityOperation,
                    ftrack_api.operation.UpdateEntityOperation,
                    ftrack_api.operation.DeleteEntityOperation
                )
            )
        ):
            key = (operation.entity_type, str(list(operation.entity_key.values())))
            if key not in entities_by_identity:
                continue

            value = _state(operation, entities_by_identity[key])
            entities_by_identity[key] = value

    return list(entities_by_identity.values())
