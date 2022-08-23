# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import math

import pytest

import ftrack_api
import ftrack_api.query
import ftrack_api.exception


def test_index(session):
    '''Index into query result.'''
    results = session.query('User')
    assert isinstance(results[2], session.types['User'])


def test_len(session):
    '''Return count of results using len.'''
    results = session.query('User where username is jenkins')
    assert len(results) == 1


def test_all(session):
    '''Return all results using convenience method.'''
    results = session.query('User').all()
    assert isinstance(results, list)
    assert len(results)


def test_implicit_iteration(session):
    '''Implicitly iterate through query result.'''
    results = session.query('User')
    assert isinstance(results, ftrack_api.query.QueryResult)

    records = []
    for record in results:
        records.append(record)

    assert len(records) == len(results)


def test_one(session):
    '''Return single result using convenience method.'''
    user = session.query('User where username is jenkins').one()
    assert user['username'] == 'jenkins'


def test_one_fails_for_no_results(session):
    '''Fail to fetch single result when no results available.'''
    with pytest.raises(ftrack_api.exception.NoResultFoundError):
        session.query('User where username is does_not_exist').one()


def test_one_fails_for_multiple_results(session):
    '''Fail to fetch single result when multiple results available.'''
    with pytest.raises(ftrack_api.exception.MultipleResultsFoundError):
        session.query('User').one()


def test_one_with_existing_limit(session):
    '''Fail to return single result when existing limit in expression.'''
    with pytest.raises(ValueError):
        session.query('User where username is jenkins limit 0').one()


def test_one_with_existing_offset(session):
    '''Fail to return single result when existing offset in expression.'''
    with pytest.raises(ValueError):
        session.query('User where username is jenkins offset 2').one()


def test_one_with_prefetched_data(session):
    '''Return single result ignoring prefetched data.'''
    query = session.query('User where username is jenkins')
    query.all()

    user = query.one()
    assert user['username'] == 'jenkins'


def test_first(session):
    '''Return first result using convenience method.'''
    users = session.query('User').all()

    user = session.query('User').first()
    assert user == users[0]


def test_first_returns_none_when_no_results(session):
    '''Return None when no results available.'''
    user = session.query('User where username is does_not_exist').first()
    assert user is None


def test_first_with_existing_limit(session):
    '''Fail to return first result when existing limit in expression.'''
    with pytest.raises(ValueError):
        session.query('User where username is jenkins limit 0').first()


def test_first_with_existing_offset(session):
    '''Return first result whilst respecting custom offset.'''
    users = session.query('User').all()

    user = session.query('User offset 2').first()
    assert user == users[2]


def test_first_with_prefetched_data(session):
    '''Return first result ignoring prefetched data.'''
    query = session.query('User where username is jenkins')
    query.all()

    user = query.first()
    assert user['username'] == 'jenkins'


def test_paging(session, mocker):
    '''Page through results.'''
    mocker.patch.object(session, 'call', wraps=session.call)

    page_size = 5
    query = session.query('User limit 50', page_size=page_size)
    records = query.all()

    assert session.call.call_count == (
        math.ceil(len(records) / float(page_size))
    )


def test_paging_respects_offset_and_limit(session, mocker):
    '''Page through results respecting offset and limit.'''
    users = session.query('User').all()

    mocker.patch.object(session, 'call', wraps=session.call)

    page_size = 6
    query = session.query('User offset 2 limit 8', page_size=page_size)
    records = query.all()

    assert session.call.call_count == 2
    assert len(records) == 8
    assert records == users[2:10]


def test_paging_respects_limit_smaller_than_page_size(session, mocker):
    '''Use initial limit when less than page size.'''
    mocker.patch.object(session, 'call', wraps=session.call)

    page_size = 100
    query = session.query('User limit 10', page_size=page_size)
    records = query.all()

    assert session.call.call_count == 1
    session.call.assert_called_once_with(
        [{
            'action': 'query',
            'expression': 'select id from User offset 0 limit 10'
        }]
    )

    assert len(records) == 10