# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import copy


class Operations(object):
    '''Stack of operations.'''

    def __init__(self):
        '''Initialise stack.'''
        self._stack = []
        super(Operations, self).__init__()

    def clear(self):
        '''Clear all operations.'''
        del self._stack[:]

    def push(self, operation):
        '''Push *operation* onto stack.'''
        self._stack.append(operation)

    def pop(self):
        '''Pop and return most recent operation from stack.'''
        return self._stack.pop()

    def __len__(self):
        '''Return count of operations.'''
        return len(self._stack)

    def __iter__(self):
        '''Return iterator over operations.'''
        return iter(self._stack)


class Operation(object):
    '''Represent an operation.'''


class CreateEntityOperation(Operation):
    '''Represent create entity operation.'''

    def __init__(self, entity_type, entity_key, entity_data):
        '''Initialise operation.

        *entity_type* should be the type of entity in string form (as returned
        from :attr:`ftrack_api.entity.base.Entity.entity_type`).

        *entity_key* should be the unique key for the entity and should follow
        the form returned from :func:`ftrack_api.inspection.primary_key`.

        *entity_data* should be a mapping of the initial data to populate the
        entity with when creating.

        .. note::

            Shallow copies will be made of each value in *entity_data*.

        '''
        super(CreateEntityOperation, self).__init__()
        self.entity_type = entity_type
        self.entity_key = entity_key
        self.entity_data = {}
        for key, value in entity_data.items():
            self.entity_data[key] = copy.copy(value)


class UpdateEntityOperation(Operation):
    '''Represent update entity operation.'''

    def __init__(
        self, entity_type, entity_key, attribute_name, old_value, new_value
    ):
        '''Initialise operation.

        *entity_type* should be the type of entity in string form (as returned
        from :attr:`ftrack_api.entity.base.Entity.entity_type`).

        *entity_key* should be the unique key for the entity and should follow
        the form returned from :func:`ftrack_api.inspection.primary_key`.

        *attribute_name* should be the string name of the attribute being
        modified and *old_value* and *new_value* should reflect the change in
        value.

        .. note::

            Shallow copies will be made of both *old_value* and *new_value*.

        '''
        super(UpdateEntityOperation, self).__init__()
        self.entity_type = entity_type
        self.entity_key = entity_key
        self.attribute_name = attribute_name
        self.old_value = copy.copy(old_value)
        self.new_value = copy.copy(new_value)


class DeleteEntityOperation(Operation):
    '''Represent delete entity operation.'''

    def __init__(self, entity_type, entity_key):
        '''Initialise operation.

        *entity_type* should be the type of entity in string form (as returned
        from :attr:`ftrack_api.entity.base.Entity.entity_type`).

        *entity_key* should be the unique key for the entity and should follow
        the form returned from :func:`ftrack_api.inspection.primary_key`.

        '''
        super(DeleteEntityOperation, self).__init__()
        self.entity_type = entity_type
        self.entity_key = entity_key

