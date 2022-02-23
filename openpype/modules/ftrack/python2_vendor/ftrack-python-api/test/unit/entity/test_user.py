# :coding: utf-8
# :copyright: Copyright (c) 2016 ftrack


def test_force_start_timer(new_user, task):
    '''Successfully force starting a timer when another timer is running.'''
    first_timer = new_user.start_timer(context=task)
    second_timer = new_user.start_timer(context=task, force=True)

    assert first_timer['id']
    assert second_timer['id']
    assert first_timer['id'] != second_timer['id']


def test_timer_creates_timelog(new_user, task, unique_name):
    '''Successfully create time log when stopping timer.

    A timer which was immediately stopped should have a duration less than
    a minute.

    '''
    comment = 'comment' + unique_name
    timer = new_user.start_timer(
        context=task,
        name=unique_name,
        comment=comment
    )
    timer_start = timer['start']
    timelog = new_user.stop_timer()

    assert timelog['user_id'] == new_user['id']
    assert timelog['context_id']== task['id']
    assert timelog['name'] == unique_name
    assert timelog['comment'] == comment
    assert timelog['start'] == timer_start
    assert isinstance(timelog['duration'], (int, long, float))
    assert timelog['duration'] < 60


def test_reset_user_api_key(new_user):
    '''Test resetting of api keys.'''

    api_keys = list()
    for i in range(0, 10):
        api_keys.append(new_user.reset_api_key())

    # make sure all api keys are unique
    assert len(set(api_keys)) == 10

