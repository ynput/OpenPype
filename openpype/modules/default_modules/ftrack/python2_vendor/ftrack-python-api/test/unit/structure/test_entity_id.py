# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import inspect

import pytest
import mock

import ftrack_api
import ftrack_api.structure.entity_id


@pytest.fixture(scope='session')
def structure():
    '''Return structure.'''
    return ftrack_api.structure.entity_id.EntityIdStructure()


# Note: When it is possible to use indirect=True on just a few arguments, the
# called functions here can change to standard fixtures.
# https://github.com/pytest-dev/pytest/issues/579

def valid_entity():
    '''Return valid entity.'''
    session = ftrack_api.Session()

    entity = session.create('FileComponent', {
        'id': 'f6cd40cb-d1c0-469f-a2d5-10369be8a724',
        'name': 'file_component',
        'file_type': '.png'
    })

    return entity


@pytest.mark.parametrize('entity, context, expected', [
    (valid_entity(), {}, 'f6cd40cb-d1c0-469f-a2d5-10369be8a724'),
    (mock.Mock(), {}, Exception)
], ids=[
    'valid-entity',
    'non-entity'
])
def test_get_resource_identifier(structure, entity, context, expected):
    '''Get resource identifier.'''
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            structure.get_resource_identifier(entity, context)
    else:
        assert structure.get_resource_identifier(entity, context) == expected
