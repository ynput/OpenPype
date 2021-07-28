# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest
import ftrack_api.exception


def test_manually_create_multiple_timers_with_error(session, new_user):
    '''Fail to create a second timer.'''
    session.create('Timer', {
        'user': new_user
    })

    session.commit()

    with pytest.raises(ftrack_api.exception.ServerError):
        session.create('Timer', {
            'user': new_user
        })

        session.commit()

    session.reset()


def test_create_multiple_timers_with_error(session, new_user):
    '''Fail to create a second timer.'''
    new_user.start_timer()

    with pytest.raises(ftrack_api.exception.NotUniqueError):
        new_user.start_timer()

    session.reset()


def test_start_and_stop_a_timer(session, new_user, new_task):
    '''Start a new timer and stop it to create a timelog.'''
    new_user.start_timer(new_task)

    new_user.stop_timer()

    timelog = session.query(
        'Timelog where context_id = "{0}"'.format(new_task['id'])
    ).one()

    assert timelog['user_id'] == new_user['id'], 'User id is correct.'
    assert timelog['context_id'] == new_task['id'], 'Task id is correct.'


def test_start_a_timer_when_timer_is_running(session, new_user, new_task):
    '''Start a timer when an existing timer is already running.'''
    new_user.start_timer(new_task)

    # Create the second timer without context.
    new_user.start_timer(force=True)

    # There should be only one existing timelog for this user.
    timelogs = session.query(
        'Timelog where user_id = "{0}"'.format(new_user['id'])
    ).all()
    assert len(timelogs) == 1, 'One timelog exists.'

    timelog = session.query(
        'Timer where user_id = "{0}"'.format(new_user['id'])
    ).one()

    # Make sure running timer has no context.
    assert timelog['context_id'] is None, 'Timer does not have a context.'


def test_stop_timer_without_timer_running(session, new_user):
    '''Stop a timer when no timer is running.'''
    with pytest.raises(ftrack_api.exception.NoResultFoundError):
        new_user.stop_timer()
