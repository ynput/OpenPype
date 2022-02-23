# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import ftrack_api.inspection
import ftrack_api.symbol


def test_identity(user):
    '''Retrieve identity of *user*.'''
    identity = ftrack_api.inspection.identity(user)
    assert identity[0] == 'User'
    assert identity[1] == ['d07ae5d0-66e1-11e1-b5e9-f23c91df25eb']


def test_primary_key(user):
    '''Retrieve primary key of *user*.'''
    primary_key = ftrack_api.inspection.primary_key(user)
    assert primary_key == {
        'id': 'd07ae5d0-66e1-11e1-b5e9-f23c91df25eb'
    }


def test_created_entity_state(session, unique_name):
    '''Created entity has CREATED state.'''
    new_user = session.create('User', {'username': unique_name})
    assert ftrack_api.inspection.state(new_user) is ftrack_api.symbol.CREATED

    # Even after a modification the state should remain as CREATED.
    new_user['username'] = 'changed'
    assert ftrack_api.inspection.state(new_user) is ftrack_api.symbol.CREATED


def test_retrieved_entity_state(user):
    '''Retrieved entity has NOT_SET state.'''
    assert ftrack_api.inspection.state(user) is ftrack_api.symbol.NOT_SET


def test_modified_entity_state(user):
    '''Modified entity has MODIFIED state.'''
    user['username'] = 'changed'
    assert ftrack_api.inspection.state(user) is ftrack_api.symbol.MODIFIED


def test_deleted_entity_state(session, user):
    '''Deleted entity has DELETED state.'''
    session.delete(user)
    assert ftrack_api.inspection.state(user) is ftrack_api.symbol.DELETED


def test_post_commit_entity_state(session, unique_name):
    '''Entity has NOT_SET state post commit.'''
    new_user = session.create('User', {'username': unique_name})
    assert ftrack_api.inspection.state(new_user) is ftrack_api.symbol.CREATED

    session.commit()

    assert ftrack_api.inspection.state(new_user) is ftrack_api.symbol.NOT_SET


def test_states(session, unique_name, user):
    '''Determine correct states for multiple entities.'''
    # NOT_SET
    user_a = session.create('User', {'username': unique_name})
    session.commit()

    # CREATED
    user_b = session.create('User', {'username': unique_name})
    user_b['username'] = 'changed'

    # MODIFIED
    user_c = user
    user_c['username'] = 'changed'

    # DELETED
    user_d = session.create('User', {'username': unique_name})
    session.delete(user_d)

    # Assert states.
    states = ftrack_api.inspection.states([user_a, user_b, user_c, user_d])

    assert states == [
        ftrack_api.symbol.NOT_SET,
        ftrack_api.symbol.CREATED,
        ftrack_api.symbol.MODIFIED,
        ftrack_api.symbol.DELETED
    ]


def test_states_for_no_entities():
    '''Return empty list of states when no entities passed.'''
    states = ftrack_api.inspection.states([])
    assert states == []


def test_skip_operations_for_non_inspected_entities(session, unique_name):
    '''Skip operations for non inspected entities.'''
    user_a = session.create('User', {'username': unique_name + '-1'})
    user_b = session.create('User', {'username': unique_name + '-2'})

    states = ftrack_api.inspection.states([user_a])
    assert states == [ftrack_api.symbol.CREATED]
