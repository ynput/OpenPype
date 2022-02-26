# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import inspect

import pytest

import ftrack_api
import ftrack_api.structure.id


@pytest.fixture(scope='session')
def structure():
    '''Return structure.'''
    return ftrack_api.structure.id.IdStructure(prefix='path')


# Note: When it is possible to use indirect=True on just a few arguments, the
# called functions here can change to standard fixtures.
# https://github.com/pytest-dev/pytest/issues/579

def file_component(container=None):
    '''Return file component.'''
    session = ftrack_api.Session()

    entity = session.create('FileComponent', {
        'id': 'f6cd40cb-d1c0-469f-a2d5-10369be8a724',
        'name': '0001',
        'file_type': '.png',
        'container': container
    })

    return entity


def sequence_component(padding=0):
    '''Return sequence component with *padding*.'''
    session = ftrack_api.Session()

    entity = session.create('SequenceComponent', {
        'id': 'ff17edad-2129-483b-8b59-d1a654c8497b',
        'name': 'sequence_component',
        'file_type': '.png',
        'padding': padding
    })

    return entity


def container_component():
    '''Return container component.'''
    session = ftrack_api.Session()

    entity = session.create('ContainerComponent', {
        'id': '03ab9967-f86c-4b55-8252-cd187d0c244a',
        'name': 'container_component'
    })

    return entity


def unsupported_entity():
    '''Return an unsupported entity.'''
    session = ftrack_api.Session()

    entity = session.create('User', {
        'username': 'martin'
    })

    return entity


@pytest.mark.parametrize('entity, context, expected', [
    (
        file_component(), {},
        'path/f/6/c/d/40cb-d1c0-469f-a2d5-10369be8a724.png'
    ),
    (
        file_component(container_component()), {},
        'path/0/3/a/b/9967-f86c-4b55-8252-cd187d0c244a/'
        'f6cd40cb-d1c0-469f-a2d5-10369be8a724.png'
    ),
    (
        file_component(sequence_component()), {},
        'path/f/f/1/7/edad-2129-483b-8b59-d1a654c8497b/file.0001.png'
    ),
    (
        sequence_component(padding=0), {},
        'path/f/f/1/7/edad-2129-483b-8b59-d1a654c8497b/file.%d.png'
    ),
    (
        sequence_component(padding=4), {},
        'path/f/f/1/7/edad-2129-483b-8b59-d1a654c8497b/file.%04d.png'
    ),
    (
        container_component(), {},
        'path/0/3/a/b/9967-f86c-4b55-8252-cd187d0c244a'
    ),
    (unsupported_entity(), {}, NotImplementedError)
], ids=[
    'file-component',
    'file-component-in-container',
    'file-component-in-sequence',
    'unpadded-sequence-component',
    'padded-sequence-component',
    'container-component',
    'unsupported-entity'
])
def test_get_resource_identifier(structure, entity, context, expected):
    '''Get resource identifier.'''
    if inspect.isclass(expected) and issubclass(expected, Exception):
        with pytest.raises(expected):
            structure.get_resource_identifier(entity, context)
    else:
        assert structure.get_resource_identifier(entity, context) == expected
