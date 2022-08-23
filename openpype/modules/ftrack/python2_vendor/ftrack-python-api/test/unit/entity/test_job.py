# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest


def test_create_job(session, user):
    '''Create job.'''
    job = session.create('Job', {
        'user': user
    })

    assert job
    session.commit()
    assert job['type'] == 'api_job'

    session.delete(job)
    session.commit()


def test_create_job_with_valid_type(session, user):
    '''Create job explicitly specifying valid type.'''
    job = session.create('Job', {
        'user': user,
        'type': 'api_job'
    })

    assert job
    session.commit()
    assert job['type'] == 'api_job'

    session.delete(job)
    session.commit()


def test_create_job_using_faulty_type(session, user):
    '''Fail to create job with faulty type.'''
    with pytest.raises(ValueError):
        session.create('Job', {
            'user': user,
            'type': 'not-allowed-type'
        })
