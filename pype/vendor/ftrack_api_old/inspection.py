# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import collections

import ftrack_api_old.symbol
import ftrack_api_old.operation


def identity(entity):
    '''Return unique identity of *entity*.'''
    return (
        str(entity.entity_type),
        primary_key(entity).values()
    )


def primary_key(entity):
    '''Return primary key of *entity* as an ordered mapping of {field: value}.

    To get just the primary key values::

        primary_key(entity).values()

    '''
    primary_key = collections.OrderedDict()
    for name in entity.primary_key_attributes:
        value = entity[name]
        if value is ftrack_api_old.symbol.NOT_SET:
            raise KeyError(
                'Missing required value for primary key attribute "{0}" on '
                'entity {1!r}.'.format(name, entity)
            )

        primary_key[str(name)] = str(value)

    return primary_key


def _state(operation, state):
    '''Return state following *operation* against current *state*.'''
    if (
        isinstance(
            operation, ftrack_api_old.operation.CreateEntityOperation
        )
        and state is ftrack_api_old.symbol.NOT_SET
    ):
        state = ftrack_api_old.symbol.CREATED

    elif (
        isinstance(
            operation, ftrack_api_old.operation.UpdateEntityOperation
        )
        and state is ftrack_api_old.symbol.NOT_SET
    ):
        state = ftrack_api_old.symbol.MODIFIED

    elif isinstance(
        operation, ftrack_api_old.operation.DeleteEntityOperation
    ):
        state = ftrack_api_old.symbol.DELETED

    return state


def state(entity):
    '''Return current *entity* state.

    .. seealso:: :func:`ftrack_api_old.inspection.states`.

    '''
    value = ftrack_api_old.symbol.NOT_SET

    for operation in entity.session.recorded_operations:
        # Determine if operation refers to an entity and whether that entity
        # is *entity*.
        if (
            isinstance(
                operation,
                (
                    ftrack_api_old.operation.CreateEntityOperation,
                    ftrack_api_old.operation.UpdateEntityOperation,
                    ftrack_api_old.operation.DeleteEntityOperation
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

    .. seealso:: :func:`ftrack_api_old.inspection.state`.

    '''
    if not entities:
        return []

    session = entities[0].session

    entities_by_identity = collections.OrderedDict()
    for entity in entities:
        key = (entity.entity_type, str(primary_key(entity).values()))
        entities_by_identity[key] = ftrack_api_old.symbol.NOT_SET

    for operation in session.recorded_operations:
        if (
            isinstance(
                operation,
                (
                    ftrack_api_old.operation.CreateEntityOperation,
                    ftrack_api_old.operation.UpdateEntityOperation,
                    ftrack_api_old.operation.DeleteEntityOperation
                )
            )
        ):
            key = (operation.entity_type, str(operation.entity_key.values()))
            if key not in entities_by_identity:
                continue

            value = _state(operation, entities_by_identity[key])
            entities_by_identity[key] = value

    return entities_by_identity.values()
