# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

from .base import Structure


class OriginStructure(Structure):
    '''Origin structure that passes through existing resource identifier.'''

    def get_resource_identifier(self, entity, context=None):
        '''Return a resource identifier for supplied *entity*.

        *context* should be a mapping that includes at least a
        'source_resource_identifier' key that refers to the resource identifier
        to pass through.

        '''
        if context is None:
            context = {}

        resource_identifier = context.get('source_resource_identifier')
        if resource_identifier is None:
            raise ValueError(
                'Could not generate resource identifier as no source resource '
                'identifier found in passed context.'
            )

        return resource_identifier
