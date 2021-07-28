# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from __future__ import absolute_import

import logging

import collections
import copy

import ftrack_api.exception
import ftrack_api.inspection
import ftrack_api.symbol
import ftrack_api.operation
import ftrack_api.cache
from ftrack_api.logging import LazyLogMessage as L


class Collection(collections.MutableSequence):
    '''A collection of entities.'''

    def __init__(self, entity, attribute, mutable=True, data=None):
        '''Initialise collection.'''
        self.entity = entity
        self.attribute = attribute
        self._data = []
        self._identities = set()

        # Set initial dataset.
        # Note: For initialisation, immutability is deferred till after initial
        # population as otherwise there would be no public way to initialise an
        # immutable collection. The reason self._data is not just set directly
        # is to ensure other logic can be applied without special handling.
        self.mutable = True
        try:
            if data is None:
                data = []

            with self.entity.session.operation_recording(False):
                self.extend(data)
        finally:
            self.mutable = mutable

    def _identity_key(self, entity):
        '''Return identity key for *entity*.'''
        return str(ftrack_api.inspection.identity(entity))

    def __copy__(self):
        '''Return shallow copy.

        .. note::

            To maintain expectations on usage, the shallow copy will include a
            shallow copy of the underlying data store.

        '''
        cls = self.__class__
        copied_instance = cls.__new__(cls)
        copied_instance.__dict__.update(self.__dict__)
        copied_instance._data = copy.copy(self._data)
        copied_instance._identities = copy.copy(self._identities)

        return copied_instance

    def _notify(self, old_value):
        '''Notify about modification.'''
        # Record operation.
        if self.entity.session.record_operations:
            self.entity.session.recorded_operations.push(
                ftrack_api.operation.UpdateEntityOperation(
                    self.entity.entity_type,
                    ftrack_api.inspection.primary_key(self.entity),
                    self.attribute.name,
                    old_value,
                    self
                )
            )

    def insert(self, index, item):
        '''Insert *item* at *index*.'''
        if not self.mutable:
            raise ftrack_api.exception.ImmutableCollectionError(self)

        if item in self:
            raise ftrack_api.exception.DuplicateItemInCollectionError(
                item, self
            )

        old_value = copy.copy(self)
        self._data.insert(index, item)
        self._identities.add(self._identity_key(item))
        self._notify(old_value)

    def __contains__(self, value):
        '''Return whether *value* present in collection.'''
        return self._identity_key(value) in self._identities

    def __getitem__(self, index):
        '''Return item at *index*.'''
        return self._data[index]

    def __setitem__(self, index, item):
        '''Set *item* against *index*.'''
        if not self.mutable:
            raise ftrack_api.exception.ImmutableCollectionError(self)

        try:
            existing_index = self.index(item)
        except ValueError:
            pass
        else:
            if index != existing_index:
                raise ftrack_api.exception.DuplicateItemInCollectionError(
                    item, self
                )

        old_value = copy.copy(self)
        try:
            existing_item = self._data[index]
        except IndexError:
            pass
        else:
            self._identities.remove(self._identity_key(existing_item))

        self._data[index] = item
        self._identities.add(self._identity_key(item))
        self._notify(old_value)

    def __delitem__(self, index):
        '''Remove item at *index*.'''
        if not self.mutable:
            raise ftrack_api.exception.ImmutableCollectionError(self)

        old_value = copy.copy(self)
        item = self._data[index]
        del self._data[index]
        self._identities.remove(self._identity_key(item))
        self._notify(old_value)

    def __len__(self):
        '''Return count of items.'''
        return len(self._data)

    def __eq__(self, other):
        '''Return whether this collection is equal to *other*.'''
        if not isinstance(other, Collection):
            return False

        return sorted(self._identities) == sorted(other._identities)

    def __ne__(self, other):
        '''Return whether this collection is not equal to *other*.'''
        return not self == other


class MappedCollectionProxy(collections.MutableMapping):
    '''Common base class for mapped collection of entities.'''

    def __init__(self, collection):
        '''Initialise proxy for *collection*.'''
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )
        self.collection = collection
        super(MappedCollectionProxy, self).__init__()

    def __copy__(self):
        '''Return shallow copy.

        .. note::

            To maintain expectations on usage, the shallow copy will include a
            shallow copy of the underlying collection.

        '''
        cls = self.__class__
        copied_instance = cls.__new__(cls)
        copied_instance.__dict__.update(self.__dict__)
        copied_instance.collection = copy.copy(self.collection)

        return copied_instance

    @property
    def mutable(self):
        '''Return whether collection is mutable.'''
        return self.collection.mutable

    @mutable.setter
    def mutable(self, value):
        '''Set whether collection is mutable to *value*.'''
        self.collection.mutable = value

    @property
    def attribute(self):
        '''Return attribute bound to.'''
        return self.collection.attribute

    @attribute.setter
    def attribute(self, value):
        '''Set bound attribute to *value*.'''
        self.collection.attribute = value


class KeyValueMappedCollectionProxy(MappedCollectionProxy):
    '''A mapped collection of key, value entities.

    Proxy a standard :class:`Collection` as a mapping where certain attributes
    from the entities in the collection are mapped to key, value pairs.

    For example::

        >>> collection = [Metadata(key='foo', value='bar'), ...]
        >>> mapped = KeyValueMappedCollectionProxy(
        ...     collection, create_metadata,
        ...     key_attribute='key', value_attribute='value'
        ... )
        >>> print mapped['foo']
        'bar'
        >>> mapped['bam'] = 'biz'
        >>> print mapped.collection[-1]
        Metadata(key='bam', value='biz')

    '''

    def __init__(
        self, collection, creator, key_attribute, value_attribute
    ):
        '''Initialise collection.'''
        self.creator = creator
        self.key_attribute = key_attribute
        self.value_attribute = value_attribute
        super(KeyValueMappedCollectionProxy, self).__init__(collection)

    def _get_entity_by_key(self, key):
        '''Return entity instance with matching *key* from collection.'''
        for entity in self.collection:
            if entity[self.key_attribute] == key:
                return entity

        raise KeyError(key)

    def __getitem__(self, key):
        '''Return value for *key*.'''
        entity = self._get_entity_by_key(key)
        return entity[self.value_attribute]

    def __setitem__(self, key, value):
        '''Set *value* for *key*.'''
        try:
            entity = self._get_entity_by_key(key)
        except KeyError:
            data = {
                self.key_attribute: key,
                self.value_attribute: value
            }
            entity = self.creator(self, data)

            if (
                ftrack_api.inspection.state(entity) is
                ftrack_api.symbol.CREATED
            ):
                # Persisting this entity will be handled here, record the
                # operation.
                self.collection.append(entity)

            else:
                # The entity is created and persisted separately by the
                # creator. Do not record this operation.
                with self.collection.entity.session.operation_recording(False):
                    # Do not record this operation since it will trigger
                    # redudant and potentially failing operations.
                    self.collection.append(entity)

        else:
            entity[self.value_attribute] = value

    def __delitem__(self, key):
        '''Remove and delete *key*.

        .. note::

            The associated entity will be deleted as well.

        '''
        for index, entity in enumerate(self.collection):
            if entity[self.key_attribute] == key:
                break
        else:
            raise KeyError(key)

        del self.collection[index]
        entity.session.delete(entity)

    def __iter__(self):
        '''Iterate over all keys.'''
        keys = set()
        for entity in self.collection:
            keys.add(entity[self.key_attribute])

        return iter(keys)

    def __len__(self):
        '''Return count of keys.'''
        keys = set()
        for entity in self.collection:
            keys.add(entity[self.key_attribute])

        return len(keys)


class PerSessionDefaultKeyMaker(ftrack_api.cache.KeyMaker):
    '''Generate key for session.'''

    def _key(self, obj):
        '''Return key for *obj*.'''
        if isinstance(obj, dict):
            session = obj.get('session')
            if session is not None:
                # Key by session only.
                return str(id(session))

        return str(obj)


#: Memoiser for use with callables that should be called once per session.
memoise_session = ftrack_api.cache.memoise_decorator(
    ftrack_api.cache.Memoiser(
        key_maker=PerSessionDefaultKeyMaker(), return_copies=False
    )
)


@memoise_session
def _get_custom_attribute_configurations(session):
    '''Return list of custom attribute configurations.

    The configuration objects will have key, project_id, id and object_type_id
    populated.

    '''
    return session.query(
        'select key, project_id, id, object_type_id, entity_type from '
        'CustomAttributeConfiguration'
    ).all()


class CustomAttributeCollectionProxy(MappedCollectionProxy):
    '''A mapped collection of custom attribute value entities.'''

    def __init__(
        self, collection
    ):
        '''Initialise collection.'''
        self.key_attribute = 'configuration_id'
        self.value_attribute = 'value'
        super(CustomAttributeCollectionProxy, self).__init__(collection)

    def _get_entity_configurations(self):
        '''Return all configurations for current collection entity.'''
        entity = self.collection.entity
        entity_type = None
        project_id = None
        object_type_id = None

        if 'object_type_id' in entity.keys():
            project_id = entity['project_id']
            entity_type = 'task'
            object_type_id = entity['object_type_id']

        if entity.entity_type == 'AssetVersion':
            project_id = entity['asset']['parent']['project_id']
            entity_type = 'assetversion'

        if entity.entity_type == 'Asset':
            project_id = entity['parent']['project_id']
            entity_type = 'asset'

        if entity.entity_type == 'Project':
            project_id = entity['id']
            entity_type = 'show'

        if entity.entity_type == 'User':
            entity_type = 'user'

        if entity_type is None:
            raise ValueError(
                'Entity {!r} not supported.'.format(entity)
            )

        configurations = []
        for configuration in _get_custom_attribute_configurations(
            entity.session
        ):
            if (
                configuration['entity_type'] == entity_type and
                configuration['project_id'] in (project_id, None) and
                configuration['object_type_id'] == object_type_id
            ):
                configurations.append(configuration)

        # Return with global configurations at the end of the list. This is done
        # so that global conigurations are shadowed by project specific if the
        # configurations list is looped when looking for a matching `key`.
        return sorted(
            configurations, key=lambda item: item['project_id'] is None
        )

    def _get_keys(self):
        '''Return a list of all keys.'''
        keys = []
        for configuration in self._get_entity_configurations():
            keys.append(configuration['key'])

        return keys

    def _get_entity_by_key(self, key):
        '''Return entity instance with matching *key* from collection.'''
        configuration_id = self.get_configuration_id_from_key(key)
        for entity in self.collection:
            if entity[self.key_attribute] == configuration_id:
                return entity

        return None

    def get_configuration_id_from_key(self, key):
        '''Return id of configuration with matching *key*.

        Raise :exc:`KeyError` if no configuration with matching *key* found.

        '''
        for configuration in self._get_entity_configurations():
            if key == configuration['key']:
                return configuration['id']

        raise KeyError(key)

    def __getitem__(self, key):
        '''Return value for *key*.'''
        entity = self._get_entity_by_key(key)

        if entity:
            return entity[self.value_attribute]

        for configuration in self._get_entity_configurations():
            if configuration['key'] == key:
                return configuration['default']

        raise KeyError(key)

    def __setitem__(self, key, value):
        '''Set *value* for *key*.'''
        custom_attribute_value = self._get_entity_by_key(key)

        if custom_attribute_value:
            custom_attribute_value[self.value_attribute] = value
        else:
            entity = self.collection.entity
            session = entity.session
            data = {
                self.key_attribute: self.get_configuration_id_from_key(key),
                self.value_attribute: value,
                'entity_id': entity['id']
            }

            # Make sure to use the currently active collection. This is
            # necessary since a merge might have replaced the current one.
            self.collection.entity['custom_attributes'].collection.append(
                session.create('CustomAttributeValue', data)
            )

    def __delitem__(self, key):
        '''Remove and delete *key*.

        .. note::

            The associated entity will be deleted as well.

        '''
        custom_attribute_value = self._get_entity_by_key(key)

        if custom_attribute_value:
            index = self.collection.index(custom_attribute_value)
            del self.collection[index]

            custom_attribute_value.session.delete(custom_attribute_value)
        else:
            self.logger.warning(L(
                'Cannot delete {0!r} on {1!r}, no custom attribute value set.',
                key, self.collection.entity
            ))

    def __eq__(self, collection):
        '''Return True if *collection* equals proxy collection.'''
        if collection is ftrack_api.symbol.NOT_SET:
            return False

        return collection.collection == self.collection

    def __iter__(self):
        '''Iterate over all keys.'''
        keys = self._get_keys()
        return iter(keys)

    def __len__(self):
        '''Return count of keys.'''
        keys = self._get_keys()
        return len(keys)
