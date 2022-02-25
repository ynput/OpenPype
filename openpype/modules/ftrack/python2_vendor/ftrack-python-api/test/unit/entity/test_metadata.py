# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import uuid

import ftrack_api


def test_query_metadata(new_project):
    '''Query metadata.'''
    session = new_project.session

    metadata_key = uuid.uuid1().hex
    metadata_value = uuid.uuid1().hex
    new_project['metadata'][metadata_key] = metadata_value
    session.commit()

    results = session.query(
        'Project where metadata.key is {0}'.format(metadata_key)
    )

    assert len(results) == 1
    assert new_project['id'] == results[0]['id']

    results = session.query(
        'Project where metadata.value is {0}'.format(metadata_value)
    )

    assert len(results) == 1
    assert new_project['id'] == results[0]['id']

    results = session.query(
        'Project where metadata.key is {0} and '
        'metadata.value is {1}'.format(metadata_key, metadata_value)
    )

    assert len(results) == 1
    assert new_project['id'] == results[0]['id']


def test_set_get_metadata_from_different_sessions(new_project):
    '''Get and set metadata using different sessions.'''
    session = new_project.session

    metadata_key = uuid.uuid1().hex
    metadata_value = uuid.uuid1().hex
    new_project['metadata'][metadata_key] = metadata_value
    session.commit()

    new_session = ftrack_api.Session()
    project = new_session.query(
        'Project where id is {0}'.format(new_project['id'])
    )[0]

    assert project['metadata'][metadata_key] == metadata_value

    project['metadata'][metadata_key] = uuid.uuid1().hex

    new_session.commit()

    new_session = ftrack_api.Session()
    project = new_session.query(
        'Project where id is {0}'.format(project['id'])
    )[0]

    assert project['metadata'][metadata_key] != metadata_value


def test_get_set_multiple_metadata(new_project):
    '''Get and set multiple metadata.'''
    session = new_project.session

    new_project['metadata'] = {
        'key1': 'value1',
        'key2': 'value2'
    }
    session.commit()

    assert set(new_project['metadata'].keys()) == set(['key1', 'key2'])

    new_session = ftrack_api.Session()
    retrieved = new_session.query(
        'Project where id is {0}'.format(new_project['id'])
    )[0]

    assert set(retrieved['metadata'].keys()) == set(['key1', 'key2'])


def test_metadata_parent_type_remains_in_schema_id_format(session, new_project):
    '''Metadata parent_type remains in schema id format post commit.'''
    entity = session.create('Metadata', {
        'key': 'key', 'value': 'value',
        'parent_type': new_project.entity_type,
        'parent_id':  new_project['id']
    })

    session.commit()

    assert entity['parent_type'] == new_project.entity_type


def test_set_metadata_twice(new_project):
    '''Set metadata twice in a row.'''
    session = new_project.session

    new_project['metadata'] = {
        'key1': 'value1',
        'key2': 'value2'
    }
    session.commit()

    assert set(new_project['metadata'].keys()) == set(['key1', 'key2'])

    new_project['metadata'] = {
        'key3': 'value3',
        'key4': 'value4'
    }
    session.commit()


def test_set_same_metadata_on_retrieved_entity(new_project):
    '''Set same metadata on retrieved entity.'''
    session = new_project.session

    new_project['metadata'] = {
        'key1': 'value1'
    }
    session.commit()

    project = session.get('Project', new_project['id'])

    project['metadata'] = {
        'key1': 'value1'
    }
    session.commit()
