# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from __future__ import absolute_import

import logging
import uuid
import functools

import ftrack_api.attribute
import ftrack_api.entity.base
import ftrack_api.entity.location
import ftrack_api.entity.component
import ftrack_api.entity.asset_version
import ftrack_api.entity.project_schema
import ftrack_api.entity.note
import ftrack_api.entity.job
import ftrack_api.entity.user
import ftrack_api.symbol
import ftrack_api.cache
from ftrack_api.logging import LazyLogMessage as L


class Factory(object):
    '''Entity class factory.'''

    def __init__(self):
        '''Initialise factory.'''
        super(Factory, self).__init__()
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

    def create(self, schema, bases=None):
        '''Create and return entity class from *schema*.

        *bases* should be a list of bases to give the constructed class. If not
        specified, default to :class:`ftrack_api.entity.base.Entity`.

        '''
        entity_type = schema['id']
        class_name = entity_type

        class_bases = bases
        if class_bases is None:
            class_bases = [ftrack_api.entity.base.Entity]

        class_namespace = dict()

        # Build attributes for class.
        attributes = ftrack_api.attribute.Attributes()
        immutable_properties = schema.get('immutable', [])
        computed_properties = schema.get('computed', [])
        for name, fragment in schema.get('properties', {}).items():
            mutable = name not in immutable_properties
            computed = name in computed_properties

            default = fragment.get('default', ftrack_api.symbol.NOT_SET)
            if default == '{uid}':
                default = lambda instance: str(uuid.uuid4())

            data_type = fragment.get('type', ftrack_api.symbol.NOT_SET)

            if data_type is not ftrack_api.symbol.NOT_SET:

                if data_type in (
                    'string', 'boolean', 'integer', 'number', 'variable',
                    'object'
                ):
                    # Basic scalar attribute.
                    if data_type == 'number':
                        data_type = 'float'

                    if data_type == 'string':
                        data_format = fragment.get('format')
                        if data_format == 'date-time':
                            data_type = 'datetime'

                    attribute = self.create_scalar_attribute(
                        class_name, name, mutable, computed, default, data_type
                    )
                    if attribute:
                        attributes.add(attribute)

                elif data_type == 'array':
                    attribute = self.create_collection_attribute(
                        class_name, name, mutable
                    )
                    if attribute:
                        attributes.add(attribute)

                elif data_type == 'mapped_array':
                    reference = fragment.get('items', {}).get('$ref')
                    if not reference:
                        self.logger.debug(L(
                            'Skipping {0}.{1} mapped_array attribute that does '
                            'not define a schema reference.', class_name, name
                        ))
                        continue

                    attribute = self.create_mapped_collection_attribute(
                        class_name, name, mutable, reference
                    )
                    if attribute:
                        attributes.add(attribute)

                else:
                    self.logger.debug(L(
                        'Skipping {0}.{1} attribute with unrecognised data '
                        'type {2}', class_name, name, data_type
                    ))
            else:
                # Reference attribute.
                reference = fragment.get('$ref', ftrack_api.symbol.NOT_SET)
                if reference is ftrack_api.symbol.NOT_SET:
                    self.logger.debug(L(
                        'Skipping {0}.{1} mapped_array attribute that does '
                        'not define a schema reference.', class_name, name
                    ))
                    continue

                attribute = self.create_reference_attribute(
                    class_name, name, mutable, reference
                )
                if attribute:
                    attributes.add(attribute)

        default_projections = schema.get('default_projections', [])

        # Construct class.
        class_namespace['entity_type'] = entity_type
        class_namespace['attributes'] = attributes
        class_namespace['primary_key_attributes'] = schema['primary_key'][:]
        class_namespace['default_projections'] = default_projections

        cls = type(
            str(class_name),  # type doesn't accept unicode.
            tuple(class_bases),
            class_namespace
        )

        return cls

    def create_scalar_attribute(
        self, class_name, name, mutable, computed, default, data_type
    ):
        '''Return appropriate scalar attribute instance.'''
        return ftrack_api.attribute.ScalarAttribute(
            name, data_type=data_type, default_value=default, mutable=mutable,
            computed=computed
        )

    def create_reference_attribute(self, class_name, name, mutable, reference):
        '''Return appropriate reference attribute instance.'''
        return ftrack_api.attribute.ReferenceAttribute(
            name, reference, mutable=mutable
        )

    def create_collection_attribute(self, class_name, name, mutable):
        '''Return appropriate collection attribute instance.'''
        return ftrack_api.attribute.CollectionAttribute(
            name, mutable=mutable
        )

    def create_mapped_collection_attribute(
        self, class_name, name, mutable, reference
    ):
        '''Return appropriate mapped collection attribute instance.'''
        self.logger.debug(L(
            'Skipping {0}.{1} mapped_array attribute that has '
            'no implementation defined for reference {2}.',
            class_name, name, reference
        ))


class PerSessionDefaultKeyMaker(ftrack_api.cache.KeyMaker):
    '''Generate key for defaults.'''

    def _key(self, obj):
        '''Return key for *obj*.'''
        if isinstance(obj, dict):
            entity = obj.get('entity')
            if entity is not None:
                # Key by session only.
                return str(id(entity.session))

        return str(obj)


#: Memoiser for use with default callables that should only be called once per
# session.
memoise_defaults = ftrack_api.cache.memoise_decorator(
    ftrack_api.cache.Memoiser(
        key_maker=PerSessionDefaultKeyMaker(), return_copies=False
    )
)

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
        'select key, project_id, id, object_type_id, entity_type, '
        'is_hierarchical from CustomAttributeConfiguration'
    ).all()


def _get_entity_configurations(entity):
    '''Return all configurations for current collection entity.'''
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

    if entity.entity_type == 'Project':
        project_id = entity['id']
        entity_type = 'show'

    if entity.entity_type == 'User':
        entity_type = 'user'

    if entity.entity_type == 'Asset':
        entity_type = 'asset'

    if entity.entity_type in ('TypedContextList', 'AssetVersionList'):
        entity_type = 'list'

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
            # The custom attribute configuration is for the target entity type.
            configurations.append(configuration)
        elif (
            entity_type in ('asset', 'assetversion', 'show', 'task') and
            configuration['project_id'] in (project_id, None) and
            configuration['is_hierarchical']
        ):
            # The target entity type allows hierarchical attributes.
            configurations.append(configuration)

    # Return with global configurations at the end of the list. This is done
    # so that global conigurations are shadowed by project specific if the
    # configurations list is looped when looking for a matching `key`.
    return sorted(
        configurations, key=lambda item: item['project_id'] is None
    )


class StandardFactory(Factory):
    '''Standard entity class factory.'''

    def create(self, schema, bases=None):
        '''Create and return entity class from *schema*.'''
        if not bases:
            bases = []

        extra_bases = []
        # Customise classes.
        if schema['id'] == 'ProjectSchema':
            extra_bases = [ftrack_api.entity.project_schema.ProjectSchema]

        elif schema['id'] == 'Location':
            extra_bases = [ftrack_api.entity.location.Location]

        elif schema['id'] == 'AssetVersion':
            extra_bases = [ftrack_api.entity.asset_version.AssetVersion]

        elif schema['id'].endswith('Component'):
            extra_bases = [ftrack_api.entity.component.Component]

        elif schema['id'] == 'Note':
            extra_bases = [ftrack_api.entity.note.Note]

        elif schema['id'] == 'Job':
            extra_bases = [ftrack_api.entity.job.Job]

        elif schema['id'] == 'User':
            extra_bases = [ftrack_api.entity.user.User]

        bases = extra_bases + bases

        # If bases does not contain any items, add the base entity class.
        if not bases:
            bases = [ftrack_api.entity.base.Entity]

        # Add mixins.
        if 'notes' in schema.get('properties', {}):
            bases.append(
                ftrack_api.entity.note.CreateNoteMixin
            )

        if 'thumbnail_id' in schema.get('properties', {}):
            bases.append(
                ftrack_api.entity.component.CreateThumbnailMixin
            )

        cls = super(StandardFactory, self).create(schema, bases=bases)

        return cls

    def create_mapped_collection_attribute(
        self, class_name, name, mutable, reference
    ):
        '''Return appropriate mapped collection attribute instance.'''
        if reference == 'Metadata':

            def create_metadata(proxy, data, reference):
                '''Return metadata for *data*.'''
                entity = proxy.collection.entity
                session = entity.session
                data.update({
                    'parent_id': entity['id'],
                    'parent_type': entity.entity_type
                })
                return session.create(reference, data)

            creator = functools.partial(
                create_metadata, reference=reference
            )
            key_attribute = 'key'
            value_attribute = 'value'

            return ftrack_api.attribute.KeyValueMappedCollectionAttribute(
                name, creator, key_attribute, value_attribute, mutable=mutable
            )

        elif reference == 'CustomAttributeValue':
            return (
                ftrack_api.attribute.CustomAttributeCollectionAttribute(
                    name, mutable=mutable
                )
            )

        elif reference.endswith('CustomAttributeValue'):
            def creator(proxy, data):
                '''Create a custom attribute based on *proxy* and *data*.

                Raise :py:exc:`KeyError` if related entity is already presisted
                to the server. The proxy represents dense custom attribute
                values and should never create new custom attribute values
                through the proxy if entity exists on the remote.

                If the entity is not persisted the ususal
                <entity_type>CustomAttributeValue items cannot be updated as
                the related entity does not exist on remote and values not in
                the proxy. Instead a <entity_type>CustomAttributeValue will
                be reconstructed and an update operation will be recorded.

                '''
                entity = proxy.collection.entity
                if (
                    ftrack_api.inspection.state(entity) is not
                    ftrack_api.symbol.CREATED
                ):
                    raise KeyError(
                        'Custom attributes must be created explicitly for the '
                        'given entity type before being set.'
                    )

                configuration = None
                for candidate in _get_entity_configurations(entity):
                    if candidate['key'] == data['key']:
                        configuration = candidate
                        break

                if configuration is None:
                    raise ValueError(
                        u'No valid custom attribute for data {0!r} was found.'
                        .format(data)
                    )

                create_data = dict(data.items())
                create_data['configuration_id'] = configuration['id']
                create_data['entity_id'] = entity['id']

                session = entity.session

                # Create custom attribute by reconstructing it and update the
                # value. This will prevent a create operation to be sent to the
                # remote, as create operations for this entity type is not
                # allowed. Instead an update operation will be recorded.
                value = create_data.pop('value')
                item = session.create(
                    reference,
                    create_data,
                    reconstructing=True
                )

                # Record update operation.
                item['value'] = value

                return item

            key_attribute = 'key'
            value_attribute = 'value'

            return ftrack_api.attribute.KeyValueMappedCollectionAttribute(
                name, creator, key_attribute, value_attribute, mutable=mutable
            )

        self.logger.debug(L(
            'Skipping {0}.{1} mapped_array attribute that has no configuration '
            'for reference {2}.', class_name, name, reference
        ))
