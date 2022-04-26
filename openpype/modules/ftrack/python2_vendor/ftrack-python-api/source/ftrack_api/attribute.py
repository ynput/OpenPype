# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from __future__ import absolute_import

import collections
import copy
import logging
import functools

import ftrack_api.symbol
import ftrack_api.exception
import ftrack_api.collection
import ftrack_api.inspection
import ftrack_api.operation

logger = logging.getLogger(
    __name__
)


def merge_references(function):
    '''Decorator to handle merging of references / collections.'''

    @functools.wraps(function)
    def get_value(attribute, entity):
        '''Merge the attribute with the local cache.'''

        if attribute.name not in entity._inflated:
            # Only merge on first access to avoid
            # inflating them multiple times.

            logger.debug(
                'Merging potential new data into attached '
                'entity for attribute {0}.'.format(
                    attribute.name
                )
            )

            # Local attributes.
            local_value = attribute.get_local_value(entity)
            if isinstance(
                local_value,
                (
                    ftrack_api.entity.base.Entity,
                    ftrack_api.collection.Collection,
                    ftrack_api.collection.MappedCollectionProxy
                )
            ):
                logger.debug(
                    'Merging local value for attribute {0}.'.format(attribute)
                )

                merged_local_value = entity.session._merge(
                    local_value, merged=dict()
                )

                if merged_local_value is not local_value:
                    with entity.session.operation_recording(False):
                        attribute.set_local_value(entity, merged_local_value)

            # Remote attributes.
            remote_value = attribute.get_remote_value(entity)
            if isinstance(
                remote_value,
                (
                    ftrack_api.entity.base.Entity,
                    ftrack_api.collection.Collection,
                    ftrack_api.collection.MappedCollectionProxy
                )
            ):
                logger.debug(
                    'Merging remote value for attribute {0}.'.format(attribute)
                )

                merged_remote_value = entity.session._merge(
                    remote_value, merged=dict()
                )

                if merged_remote_value is not remote_value:
                    attribute.set_remote_value(entity, merged_remote_value)

            entity._inflated.add(
                attribute.name
            )

        return function(
            attribute, entity
        )

    return get_value


class Attributes(object):
    '''Collection of properties accessible by name.'''

    def __init__(self, attributes=None):
        super(Attributes, self).__init__()
        self._data = dict()
        if attributes is not None:
            for attribute in attributes:
                self.add(attribute)

    def add(self, attribute):
        '''Add *attribute*.'''
        existing = self._data.get(attribute.name, None)
        if existing:
            raise ftrack_api.exception.NotUniqueError(
                'Attribute with name {0} already added as {1}'
                .format(attribute.name, existing)
            )

        self._data[attribute.name] = attribute

    def remove(self, attribute):
        '''Remove attribute.'''
        self._data.pop(attribute.name)

    def get(self, name):
        '''Return attribute by *name*.

        If no attribute matches *name* then return None.

        '''
        return self._data.get(name, None)

    def keys(self):
        '''Return list of attribute names.'''
        return self._data.keys()

    def __contains__(self, item):
        '''Return whether *item* present.'''
        if not isinstance(item, Attribute):
            return False

        return item.name in self._data

    def __iter__(self):
        '''Return iterator over attributes.'''
        return self._data.itervalues()

    def __len__(self):
        '''Return count of attributes.'''
        return len(self._data)


class Attribute(object):
    '''A name and value pair persisted remotely.'''

    def __init__(
        self, name, default_value=ftrack_api.symbol.NOT_SET, mutable=True,
        computed=False
    ):
        '''Initialise attribute with *name*.

        *default_value* represents the default value for the attribute. It may
        be a callable. It is not used within the attribute when providing
        values, but instead exists for other parts of the system to reference.

        If *mutable* is set to False then the local value of the attribute on an
        entity can only be set when both the existing local and remote values
        are :attr:`ftrack_api.symbol.NOT_SET`. The exception to this is when the
        target value is also :attr:`ftrack_api.symbol.NOT_SET`.

        If *computed* is set to True the value is a remote side computed value
        and should not be long-term cached.

        '''
        super(Attribute, self).__init__()
        self._name = name
        self._mutable = mutable
        self._computed = computed
        self.default_value = default_value

        self._local_key = 'local'
        self._remote_key = 'remote'

    def __repr__(self):
        '''Return representation of entity.'''
        return '<{0}.{1}({2}) object at {3}>'.format(
            self.__module__,
            self.__class__.__name__,
            self.name,
            id(self)
        )

    def get_entity_storage(self, entity):
        '''Return attribute storage on *entity* creating if missing.'''
        storage_key = '_ftrack_attribute_storage'
        storage = getattr(entity, storage_key, None)
        if storage is None:
            storage = collections.defaultdict(
                lambda:
                {
                    self._local_key: ftrack_api.symbol.NOT_SET,
                    self._remote_key: ftrack_api.symbol.NOT_SET
                }
            )
            setattr(entity, storage_key, storage)

        return storage

    @property
    def name(self):
        '''Return name.'''
        return self._name

    @property
    def mutable(self):
        '''Return whether attribute is mutable.'''
        return self._mutable

    @property
    def computed(self):
        '''Return whether attribute is computed.'''
        return self._computed

    def get_value(self, entity):
        '''Return current value for *entity*.

        If a value was set locally then return it, otherwise return last known
        remote value. If no remote value yet retrieved, make a request for it
        via the session and block until available.

        '''
        value = self.get_local_value(entity)
        if value is not ftrack_api.symbol.NOT_SET:
            return value

        value = self.get_remote_value(entity)
        if value is not ftrack_api.symbol.NOT_SET:
            return value

        if not entity.session.auto_populate:
            return value

        self.populate_remote_value(entity)
        return self.get_remote_value(entity)

    def get_local_value(self, entity):
        '''Return locally set value for *entity*.'''
        storage = self.get_entity_storage(entity)
        return storage[self.name][self._local_key]

    def get_remote_value(self, entity):
        '''Return remote value for *entity*.

        .. note::

            Only return locally stored remote value, do not fetch from remote.

        '''
        storage = self.get_entity_storage(entity)
        return storage[self.name][self._remote_key]

    def set_local_value(self, entity, value):
        '''Set local *value* for *entity*.'''
        if (
            not self.mutable
            and self.is_set(entity)
            and value is not ftrack_api.symbol.NOT_SET
        ):
            raise ftrack_api.exception.ImmutableAttributeError(self)

        old_value = self.get_local_value(entity)

        storage = self.get_entity_storage(entity)
        storage[self.name][self._local_key] = value

        # Record operation.
        if entity.session.record_operations:
            entity.session.recorded_operations.push(
                ftrack_api.operation.UpdateEntityOperation(
                    entity.entity_type,
                    ftrack_api.inspection.primary_key(entity),
                    self.name,
                    old_value,
                    value
                )
            )

    def set_remote_value(self, entity, value):
        '''Set remote *value*.

        .. note::

            Only set locally stored remote value, do not persist to remote.

        '''
        storage = self.get_entity_storage(entity)
        storage[self.name][self._remote_key] = value

    def populate_remote_value(self, entity):
        '''Populate remote value for *entity*.'''
        entity.session.populate([entity], self.name)

    def is_modified(self, entity):
        '''Return whether local value set and differs from remote.

        .. note::

            Will not fetch remote value so may report True even when values
            are the same on the remote.

        '''
        local_value = self.get_local_value(entity)
        remote_value = self.get_remote_value(entity)
        return (
            local_value is not ftrack_api.symbol.NOT_SET
            and local_value != remote_value
        )

    def is_set(self, entity):
        '''Return whether a value is set for *entity*.'''
        return any([
            self.get_local_value(entity) is not ftrack_api.symbol.NOT_SET,
            self.get_remote_value(entity) is not ftrack_api.symbol.NOT_SET
        ])


class ScalarAttribute(Attribute):
    '''Represent a scalar value.'''

    def __init__(self, name, data_type, **kw):
        '''Initialise property.'''
        super(ScalarAttribute, self).__init__(name, **kw)
        self.data_type = data_type


class ReferenceAttribute(Attribute):
    '''Reference another entity.'''

    def __init__(self, name, entity_type, **kw):
        '''Initialise property.'''
        super(ReferenceAttribute, self).__init__(name, **kw)
        self.entity_type = entity_type

    def populate_remote_value(self, entity):
        '''Populate remote value for *entity*.

        As attribute references another entity, use that entity's configured
        default projections to auto populate useful attributes when loading.

        '''
        reference_entity_type = entity.session.types[self.entity_type]
        default_projections = reference_entity_type.default_projections

        projections = []
        if default_projections:
            for projection in default_projections:
                projections.append('{0}.{1}'.format(self.name, projection))
        else:
            projections.append(self.name)

        entity.session.populate([entity], ', '.join(projections))

    def is_modified(self, entity):
        '''Return whether a local value has been set and differs from remote.

        .. note::

            Will not fetch remote value so may report True even when values
            are the same on the remote.

        '''
        local_value = self.get_local_value(entity)
        remote_value = self.get_remote_value(entity)

        if local_value is ftrack_api.symbol.NOT_SET:
            return False

        if remote_value is ftrack_api.symbol.NOT_SET:
            return True

        if (
            ftrack_api.inspection.identity(local_value)
            != ftrack_api.inspection.identity(remote_value)
        ):
            return True

        return False


    @merge_references
    def get_value(self, entity):
        return super(ReferenceAttribute, self).get_value(
            entity
        )

class AbstractCollectionAttribute(Attribute):
    '''Base class for collection attributes.'''

    #: Collection class used by attribute.
    collection_class = None

    @merge_references
    def get_value(self, entity):
        '''Return current value for *entity*.

        If a value was set locally then return it, otherwise return last known
        remote value. If no remote value yet retrieved, make a request for it
        via the session and block until available.

        .. note::

            As value is a collection that is mutable, will transfer a remote
            value into the local value on access if no local value currently
            set.

        '''
        super(AbstractCollectionAttribute, self).get_value(entity)

        # Conditionally, copy remote value into local value so that it can be
        # mutated without side effects.
        local_value = self.get_local_value(entity)
        remote_value = self.get_remote_value(entity)
        if (
            local_value is ftrack_api.symbol.NOT_SET
            and isinstance(remote_value, self.collection_class)
        ):
            try:
                with entity.session.operation_recording(False):
                    self.set_local_value(entity, copy.copy(remote_value))
            except ftrack_api.exception.ImmutableAttributeError:
                pass

        value = self.get_local_value(entity)

        # If the local value is still not set then attempt to set it with a
        # suitable placeholder collection so that the caller can interact with
        # the collection using its normal interface. This is required for a
        # newly created entity for example. It *could* be done as a simple
        # default value, but that would incur cost for every collection even
        # when they are not modified before commit.
        if value is ftrack_api.symbol.NOT_SET:
            try:
                with entity.session.operation_recording(False):
                    self.set_local_value(
                        entity,
                        # None should be treated as empty collection.
                        None
                    )
            except ftrack_api.exception.ImmutableAttributeError:
                pass

        return self.get_local_value(entity)

    def set_local_value(self, entity, value):
        '''Set local *value* for *entity*.'''
        if value is not ftrack_api.symbol.NOT_SET:
            value = self._adapt_to_collection(entity, value)
            value.mutable = self.mutable

        super(AbstractCollectionAttribute, self).set_local_value(entity, value)

    def set_remote_value(self, entity, value):
        '''Set remote *value*.

        .. note::

            Only set locally stored remote value, do not persist to remote.

        '''
        if value is not ftrack_api.symbol.NOT_SET:
            value = self._adapt_to_collection(entity, value)
            value.mutable = False

        super(AbstractCollectionAttribute, self).set_remote_value(entity, value)

    def _adapt_to_collection(self, entity, value):
        '''Adapt *value* to appropriate collection instance for *entity*.

        .. note::

            If *value* is None then return a suitable empty collection.

        '''
        raise NotImplementedError()


class CollectionAttribute(AbstractCollectionAttribute):
    '''Represent a collection of other entities.'''

    #: Collection class used by attribute.
    collection_class = ftrack_api.collection.Collection

    def _adapt_to_collection(self, entity, value):
        '''Adapt *value* to a Collection instance on *entity*.'''

        if not isinstance(value, ftrack_api.collection.Collection):

            if value is None:
                value = ftrack_api.collection.Collection(entity, self)

            elif isinstance(value, list):
                value = ftrack_api.collection.Collection(
                    entity, self, data=value
                )

            else:
                raise NotImplementedError(
                    'Cannot convert {0!r} to collection.'.format(value)
                )

        else:
            if value.attribute is not self:
                raise ftrack_api.exception.AttributeError(
                    'Collection already bound to a different attribute'
                )

        return value


class KeyValueMappedCollectionAttribute(AbstractCollectionAttribute):
    '''Represent a mapped key, value collection of entities.'''

    #: Collection class used by attribute.
    collection_class = ftrack_api.collection.KeyValueMappedCollectionProxy

    def __init__(
        self, name, creator, key_attribute, value_attribute, **kw
    ):
        '''Initialise attribute with *name*.

        *creator* should be a function that accepts a dictionary of data and
        is used by the referenced collection to create new entities in the
        collection.

        *key_attribute* should be the name of the attribute on an entity in
        the collection that represents the value for 'key' of the dictionary.

        *value_attribute* should be the name of the attribute on an entity in
        the collection that represents the value for 'value' of the dictionary.

        '''
        self.creator = creator
        self.key_attribute = key_attribute
        self.value_attribute = value_attribute

        super(KeyValueMappedCollectionAttribute, self).__init__(name, **kw)

    def _adapt_to_collection(self, entity, value):
        '''Adapt *value* to an *entity*.'''
        if not isinstance(
            value, ftrack_api.collection.KeyValueMappedCollectionProxy
        ):

            if value is None:
                value = ftrack_api.collection.KeyValueMappedCollectionProxy(
                    ftrack_api.collection.Collection(entity, self),
                    self.creator, self.key_attribute,
                    self.value_attribute
                )

            elif isinstance(value, (list, ftrack_api.collection.Collection)):

                if isinstance(value, list):
                    value = ftrack_api.collection.Collection(
                        entity, self, data=value
                    )

                value = ftrack_api.collection.KeyValueMappedCollectionProxy(
                    value, self.creator, self.key_attribute,
                    self.value_attribute
                )

            elif isinstance(value, collections.Mapping):
                # Convert mapping.
                # TODO: When backend model improves, revisit this logic.
                # First get existing value and delete all references. This is
                # needed because otherwise they will not be automatically
                # removed server side.
                # The following should not cause recursion as the internal
                # values should be mapped collections already.
                current_value = self.get_value(entity)
                if not isinstance(
                    current_value,
                    ftrack_api.collection.KeyValueMappedCollectionProxy
                ):
                    raise NotImplementedError(
                        'Cannot adapt mapping to collection as current value '
                        'type is not a KeyValueMappedCollectionProxy.'
                    )

                # Create the new collection using the existing collection as
                # basis. Then update through proxy interface to ensure all
                # internal operations called consistently (such as entity
                # deletion for key removal).
                collection = ftrack_api.collection.Collection(
                    entity, self, data=current_value.collection[:]
                )
                collection_proxy = (
                    ftrack_api.collection.KeyValueMappedCollectionProxy(
                        collection, self.creator,
                        self.key_attribute, self.value_attribute
                    )
                )

                # Remove expired keys from collection.
                expired_keys = set(current_value.keys()) - set(value.keys())
                for key in expired_keys:
                    del collection_proxy[key]

                # Set new values for existing keys / add new keys.
                for key, value in value.items():
                    collection_proxy[key] = value

                value = collection_proxy

            else:
                raise NotImplementedError(
                    'Cannot convert {0!r} to collection.'.format(value)
                )
        else:
            if value.attribute is not self:
                raise ftrack_api.exception.AttributeError(
                    'Collection already bound to a different attribute.'
                )

        return value


class CustomAttributeCollectionAttribute(AbstractCollectionAttribute):
    '''Represent a mapped custom attribute collection of entities.'''

    #: Collection class used by attribute.
    collection_class = (
        ftrack_api.collection.CustomAttributeCollectionProxy
    )

    def _adapt_to_collection(self, entity, value):
        '''Adapt *value* to an *entity*.'''
        if not isinstance(
            value, ftrack_api.collection.CustomAttributeCollectionProxy
        ):

            if value is None:
                value = ftrack_api.collection.CustomAttributeCollectionProxy(
                    ftrack_api.collection.Collection(entity, self)
                )

            elif isinstance(value, (list, ftrack_api.collection.Collection)):

                # Why are we creating a new if it is a list? This will cause
                # any merge to create a new proxy and collection.
                if isinstance(value, list):
                    value = ftrack_api.collection.Collection(
                        entity, self, data=value
                    )

                value = ftrack_api.collection.CustomAttributeCollectionProxy(
                    value
                )

            elif isinstance(value, collections.Mapping):
                # Convert mapping.
                # TODO: When backend model improves, revisit this logic.
                # First get existing value and delete all references. This is
                # needed because otherwise they will not be automatically
                # removed server side.
                # The following should not cause recursion as the internal
                # values should be mapped collections already.
                current_value = self.get_value(entity)
                if not isinstance(
                    current_value,
                    ftrack_api.collection.CustomAttributeCollectionProxy
                ):
                    raise NotImplementedError(
                        'Cannot adapt mapping to collection as current value '
                        'type is not a MappedCollectionProxy.'
                    )

                # Create the new collection using the existing collection as
                # basis. Then update through proxy interface to ensure all
                # internal operations called consistently (such as entity
                # deletion for key removal).
                collection = ftrack_api.collection.Collection(
                    entity, self, data=current_value.collection[:]
                )
                collection_proxy = (
                    ftrack_api.collection.CustomAttributeCollectionProxy(
                        collection
                    )
                )

                # Remove expired keys from collection.
                expired_keys = set(current_value.keys()) - set(value.keys())
                for key in expired_keys:
                    del collection_proxy[key]

                # Set new values for existing keys / add new keys.
                for key, value in value.items():
                    collection_proxy[key] = value

                value = collection_proxy

            else:
                raise NotImplementedError(
                    'Cannot convert {0!r} to collection.'.format(value)
                )
        else:
            if value.attribute is not self:
                raise ftrack_api.exception.AttributeError(
                    'Collection already bound to a different attribute.'
                )

        return value
