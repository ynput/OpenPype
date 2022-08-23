# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest

import ftrack_api.resource_identifier_transformer.base as _transformer


@pytest.fixture()
def transformer(session):
    '''Return instance of ResourceIdentifierTransformer.'''
    return _transformer.ResourceIdentifierTransformer(session)


@pytest.mark.parametrize('resource_identifier, context, expected', [
    ('identifier', None, 'identifier'),
    ('identifier', {'user': {'username': 'user'}}, 'identifier')
], ids=[
    'no context',
    'basic context'
])
def test_encode(transformer, resource_identifier, context, expected):
    '''Encode resource identifier.'''
    assert transformer.encode(resource_identifier, context) == expected


@pytest.mark.parametrize('resource_identifier, context, expected', [
    ('identifier', None, 'identifier'),
    ('identifier', {'user': {'username': 'user'}}, 'identifier')
], ids=[
    'no context',
    'basic context'
])
def test_decode(transformer, resource_identifier, context, expected):
    '''Encode resource identifier.'''
    assert transformer.decode(resource_identifier, context) == expected
