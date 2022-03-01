# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import sys
import traceback

import ftrack_api.entity.base


class Error(Exception):
    '''ftrack specific error.'''

    default_message = 'Unspecified error occurred.'

    def __init__(self, message=None, details=None):
        '''Initialise exception with *message*.

        If *message* is None, the class 'default_message' will be used.

        *details* should be a mapping of extra information that can be used in
        the message and also to provide more context.

        '''
        if message is None:
            message = self.default_message

        self.message = message
        self.details = details
        if self.details is None:
            self.details = {}

        self.traceback = traceback.format_exc()

    def __str__(self):
        '''Return string representation.'''
        keys = {}
        for key, value in self.details.iteritems():
            if isinstance(value, unicode):
                value = value.encode(sys.getfilesystemencoding())
            keys[key] = value

        return str(self.message.format(**keys))


class AuthenticationError(Error):
    '''Raise when an authentication error occurs.'''

    default_message = 'Authentication error.'


class ServerError(Error):
    '''Raise when the server reports an error.'''

    default_message = 'Server reported error processing request.'


class ServerCompatibilityError(ServerError):
    '''Raise when server appears incompatible.'''

    default_message = 'Server incompatible.'


class NotFoundError(Error):
    '''Raise when something that should exist is not found.'''

    default_message = 'Not found.'


class NotUniqueError(Error):
    '''Raise when unique value required and duplicate detected.'''

    default_message = 'Non-unique value detected.'


class IncorrectResultError(Error):
    '''Raise when a result is incorrect.'''

    default_message = 'Incorrect result detected.'


class NoResultFoundError(IncorrectResultError):
    '''Raise when a result was expected but no result was found.'''

    default_message = 'Expected result, but no result was found.'


class MultipleResultsFoundError(IncorrectResultError):
    '''Raise when a single result expected, but multiple results found.'''

    default_message = 'Expected single result, but received multiple results.'


class EntityTypeError(Error):
    '''Raise when an entity type error occurs.'''

    default_message = 'Entity type error.'


class UnrecognisedEntityTypeError(EntityTypeError):
    '''Raise when an unrecognised entity type detected.'''

    default_message = 'Entity type "{entity_type}" not recognised.'

    def __init__(self, entity_type, **kw):
        '''Initialise with *entity_type* that is unrecognised.'''
        kw.setdefault('details', {}).update(dict(
            entity_type=entity_type
        ))
        super(UnrecognisedEntityTypeError, self).__init__(**kw)


class OperationError(Error):
    '''Raise when an operation error occurs.'''

    default_message = 'Operation error.'


class InvalidStateError(Error):
    '''Raise when an invalid state detected.'''

    default_message = 'Invalid state.'


class InvalidStateTransitionError(InvalidStateError):
    '''Raise when an invalid state transition detected.'''

    default_message = (
        'Invalid transition from {current_state!r} to {target_state!r} state '
        'for entity {entity!r}'
    )

    def __init__(self, current_state, target_state, entity, **kw):
        '''Initialise error.'''
        kw.setdefault('details', {}).update(dict(
            current_state=current_state,
            target_state=target_state,
            entity=entity
        ))
        super(InvalidStateTransitionError, self).__init__(**kw)


class AttributeError(Error):
    '''Raise when an error related to an attribute occurs.'''

    default_message = 'Attribute error.'


class ImmutableAttributeError(AttributeError):
    '''Raise when modification of immutable attribute attempted.'''

    default_message = (
        'Cannot modify value of immutable {attribute.name!r} attribute.'
    )

    def __init__(self, attribute, **kw):
        '''Initialise error.'''
        kw.setdefault('details', {}).update(dict(
            attribute=attribute
        ))
        super(ImmutableAttributeError, self).__init__(**kw)


class CollectionError(Error):
    '''Raise when an error related to collections occurs.'''

    default_message = 'Collection error.'

    def __init__(self, collection, **kw):
        '''Initialise error.'''
        kw.setdefault('details', {}).update(dict(
            collection=collection
        ))
        super(CollectionError, self).__init__(**kw)


class ImmutableCollectionError(CollectionError):
    '''Raise when modification of immutable collection attempted.'''

    default_message = (
        'Cannot modify value of immutable collection {collection!r}.'
    )


class DuplicateItemInCollectionError(CollectionError):
    '''Raise when duplicate item in collection detected.'''

    default_message = (
        'Item {item!r} already exists in collection {collection!r}.'
    )

    def __init__(self, item, collection, **kw):
        '''Initialise error.'''
        kw.setdefault('details', {}).update(dict(
            item=item
        ))
        super(DuplicateItemInCollectionError, self).__init__(collection, **kw)


class ParseError(Error):
    '''Raise when a parsing error occurs.'''

    default_message = 'Failed to parse.'


class EventHubError(Error):
    '''Raise when issues related to event hub occur.'''

    default_message = 'Event hub error occurred.'


class EventHubConnectionError(EventHubError):
    '''Raise when event hub encounters connection problem.'''

    default_message = 'Event hub is not connected.'


class EventHubPacketError(EventHubError):
    '''Raise when event hub encounters an issue with a packet.'''

    default_message = 'Invalid packet.'


class PermissionDeniedError(Error):
    '''Raise when permission is denied.'''

    default_message = 'Permission denied.'


class LocationError(Error):
    '''Base for errors associated with locations.'''

    default_message = 'Unspecified location error'


class ComponentNotInAnyLocationError(LocationError):
    '''Raise when component not available in any location.'''

    default_message = 'Component not available in any location.'


class ComponentNotInLocationError(LocationError):
    '''Raise when component(s) not in location.'''

    default_message = (
        'Component(s) {formatted_components} not found in location {location}.'
    )

    def __init__(self, components, location, **kw):
        '''Initialise with *components* and *location*.'''
        if isinstance(components, ftrack_api.entity.base.Entity):
            components = [components]

        kw.setdefault('details', {}).update(dict(
            components=components,
            formatted_components=', '.join(
                [str(component) for component in components]
            ),
            location=location
        ))

        super(ComponentNotInLocationError, self).__init__(**kw)


class ComponentInLocationError(LocationError):
    '''Raise when component(s) already exists in location.'''

    default_message = (
        'Component(s) {formatted_components} already exist in location '
        '{location}.'
    )

    def __init__(self, components, location, **kw):
        '''Initialise with *components* and *location*.'''
        if isinstance(components, ftrack_api.entity.base.Entity):
            components = [components]

        kw.setdefault('details', {}).update(dict(
            components=components,
            formatted_components=', '.join(
                [str(component) for component in components]
            ),
            location=location
        ))

        super(ComponentInLocationError, self).__init__(**kw)


class AccessorError(Error):
    '''Base for errors associated with accessors.'''

    default_message = 'Unspecified accessor error'


class AccessorOperationFailedError(AccessorError):
    '''Base for failed operations on accessors.'''

    default_message = 'Operation {operation} failed: {error}'

    def __init__(
        self, operation='', resource_identifier=None, error=None, **kw
    ):
        kw.setdefault('details', {}).update(dict(
            operation=operation,
            resource_identifier=resource_identifier,
            error=error
        ))
        super(AccessorOperationFailedError, self).__init__(**kw)


class AccessorUnsupportedOperationError(AccessorOperationFailedError):
    '''Raise when operation is unsupported.'''

    default_message = 'Operation {operation} unsupported.'


class AccessorPermissionDeniedError(AccessorOperationFailedError):
    '''Raise when permission denied.'''

    default_message = (
        'Cannot {operation} {resource_identifier}. Permission denied.'
    )


class AccessorResourceIdentifierError(AccessorError):
    '''Raise when a error related to a resource_identifier occurs.'''

    default_message = 'Resource identifier is invalid: {resource_identifier}.'

    def __init__(self, resource_identifier, **kw):
        kw.setdefault('details', {}).update(dict(
            resource_identifier=resource_identifier
        ))
        super(AccessorResourceIdentifierError, self).__init__(**kw)


class AccessorFilesystemPathError(AccessorResourceIdentifierError):
    '''Raise when a error related to an accessor filesystem path occurs.'''

    default_message = (
        'Could not determine filesystem path from resource identifier: '
        '{resource_identifier}.'
    )


class AccessorResourceError(AccessorError):
    '''Base for errors associated with specific resource.'''

    default_message = 'Unspecified resource error: {resource_identifier}'

    def __init__(self, operation='', resource_identifier=None, error=None,
                 **kw):
        kw.setdefault('details', {}).update(dict(
            operation=operation,
            resource_identifier=resource_identifier
        ))
        super(AccessorResourceError, self).__init__(**kw)


class AccessorResourceNotFoundError(AccessorResourceError):
    '''Raise when a required resource is not found.'''

    default_message = 'Resource not found: {resource_identifier}'


class AccessorParentResourceNotFoundError(AccessorResourceError):
    '''Raise when a parent resource (such as directory) is not found.'''

    default_message = 'Parent resource is missing: {resource_identifier}'


class AccessorResourceInvalidError(AccessorResourceError):
    '''Raise when a resource is not the right type.'''

    default_message = 'Resource invalid: {resource_identifier}'


class AccessorContainerNotEmptyError(AccessorResourceError):
    '''Raise when container is not empty.'''

    default_message = 'Container is not empty: {resource_identifier}'


class StructureError(Error):
    '''Base for errors associated with structures.'''

    default_message = 'Unspecified structure error'


class ConnectionClosedError(Error):
    '''Raise when attempt to use closed connection detected.'''

    default_message = "Connection closed."
