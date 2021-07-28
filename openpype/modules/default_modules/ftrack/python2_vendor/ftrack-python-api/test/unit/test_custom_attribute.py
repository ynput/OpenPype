# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import uuid

import pytest

import ftrack_api

@pytest.fixture(
    params=[
        'AssetVersion', 'Shot', 'AssetVersionList', 'TypedContextList', 'User',
        'Asset'
    ]
)
def new_entity_and_custom_attribute(request, session):
    '''Return tuple with new entity, custom attribute name and value.'''
    if request.param == 'AssetVersion':
        entity = session.create(
            request.param, {
                'asset': session.query('Asset').first()
            }
        )
        return (entity, 'versiontest', 123)

    elif request.param == 'Shot':
        sequence = session.query('Sequence').first()
        entity = session.create(
            request.param, {
                'parent_id': sequence['id'],
                'project_id': sequence['project_id'],
                'name': str(uuid.uuid1())
            }
        )
        return (entity, 'fstart', 1005)

    elif request.param == 'Asset':
        shot = session.query('Shot').first()
        entity = session.create(
            request.param, {
                'context_id': shot['project_id'],
                'name': str(uuid.uuid1())
            }
        )
        return (entity, 'htest', 1005)

    elif request.param in ('AssetVersionList', 'TypedContextList'):
        entity = session.create(
            request.param, {
                'project_id': session.query('Project').first()['id'],
                'category_id': session.query('ListCategory').first()['id'],
                'name': str(uuid.uuid1())
            }
        )
        return (entity, 'listbool', True)

    elif request.param == 'User':
        entity = session.create(
            request.param, {
                'first_name': 'Custom attribute test',
                'last_name': 'Custom attribute test',
                'username': str(uuid.uuid1())
            }
        )
        return (entity, 'teststring', 'foo')


@pytest.mark.parametrize(
    'entity_type, entity_model_name, custom_attribute_name',
    [
        ('Task', 'task', 'customNumber'),
        ('AssetVersion', 'assetversion', 'NumberField')
    ],
    ids=[
        'task',
        'asset_version'
    ]
)
def test_read_set_custom_attribute(
    session, entity_type, entity_model_name, custom_attribute_name
):
    '''Retrieve custom attribute value set on instance.'''
    custom_attribute_value = session.query(
        'CustomAttributeValue where configuration.key is '
        '{custom_attribute_name}'
        .format(
            custom_attribute_name=custom_attribute_name
        )
    ).first()

    entity = session.query(
        'select custom_attributes from {entity_type} where id is '
        '{entity_id}'.format(
            entity_type=entity_type,
            entity_id=custom_attribute_value['entity_id'],
        )
    ).first()

    assert custom_attribute_value

    assert entity['id'] == entity['custom_attributes'].collection.entity['id']
    assert entity is entity['custom_attributes'].collection.entity
    assert (
        entity['custom_attributes'][custom_attribute_name] ==
        custom_attribute_value['value']
    )

    assert custom_attribute_name in entity['custom_attributes'].keys()


@pytest.mark.parametrize(
    'entity_type, custom_attribute_name',
    [
        ('Task', 'customNumber'),
        ('Shot', 'fstart'),
        (
            'AssetVersion', 'NumberField'
        )
    ],
    ids=[
        'task',
        'shot',
        'asset_version'
    ]
)
def test_write_set_custom_attribute_value(
    session, entity_type, custom_attribute_name
):
    '''Overwrite existing instance level custom attribute value.'''
    entity = session.query(
        'select custom_attributes from {entity_type} where '
        'custom_attributes.configuration.key is {custom_attribute_name}'.format(
            entity_type=entity_type,
            custom_attribute_name=custom_attribute_name
        )
    ).first()

    entity['custom_attributes'][custom_attribute_name] = 42

    assert entity['custom_attributes'][custom_attribute_name] == 42

    session.commit()


@pytest.mark.parametrize(
    'entity_type, custom_attribute_name',
    [
        ('Task', 'fstart'),
        ('Shot', 'Not existing'),
        ('AssetVersion', 'fstart')
    ],
    ids=[
        'task',
        'shot',
        'asset_version'
    ]
)
def test_read_custom_attribute_that_does_not_exist(
    session, entity_type, custom_attribute_name
):
    '''Fail to read value from a custom attribute that does not exist.'''
    entity = session.query(
        'select custom_attributes from {entity_type}'.format(
            entity_type=entity_type
        )
    ).first()

    with pytest.raises(KeyError):
        entity['custom_attributes'][custom_attribute_name]


@pytest.mark.parametrize(
    'entity_type, custom_attribute_name',
    [
        ('Task', 'fstart'),
        ('Shot', 'Not existing'),
        ('AssetVersion', 'fstart')
    ],
    ids=[
        'task',
        'shot',
        'asset_version'
    ]
)
def test_write_custom_attribute_that_does_not_exist(
    session, entity_type, custom_attribute_name
):
    '''Fail to write a value to a custom attribute that does not exist.'''
    entity = session.query(
        'select custom_attributes from {entity_type}'.format(
            entity_type=entity_type
        )
    ).first()

    with pytest.raises(KeyError):
        entity['custom_attributes'][custom_attribute_name] = 42


def test_set_custom_attribute_on_new_but_persisted_version(
    session, new_asset_version
):
    '''Set custom attribute on new persisted version.'''
    new_asset_version['custom_attributes']['versiontest'] = 5
    session.commit()


@pytest.mark.xfail(
    raises=ftrack_api.exception.ServerError, 
    reason='Due to user permission errors.'
)
def test_batch_create_entity_and_custom_attributes(
    new_entity_and_custom_attribute
):
    '''Write custom attribute value and entity in the same batch.'''
    entity, name, value = new_entity_and_custom_attribute
    session = entity.session
    entity['custom_attributes'][name] = value

    assert entity['custom_attributes'][name] == value
    session.commit()

    assert entity['custom_attributes'][name] == value


def test_refresh_custom_attribute(new_asset_version):
    '''Test custom attribute refresh.'''
    session_two = ftrack_api.Session()

    query_string = 'select custom_attributes from AssetVersion where id is "{0}"'.format(
        new_asset_version.get('id')
    )

    asset_version_two = session_two.query(
        query_string
    ).first()

    new_asset_version['custom_attributes']['versiontest'] = 42

    new_asset_version.session.commit()

    asset_version_two = session_two.query(
        query_string
    ).first()

    assert (
        new_asset_version['custom_attributes']['versiontest'] ==
        asset_version_two['custom_attributes']['versiontest']
    )



