# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.event.base


def test_string_representation():
    '''String representation.'''
    event = ftrack_api.event.base.Event('test', id='some-id')
    assert str(event) == (
        "<Event {'topic': 'test', 'source': {}, 'target': '', 'data': {}, "
        "'in_reply_to_event': None, 'id': 'some-id', 'sent': None}>"
    )


def test_stop():
    '''Set stopped flag on event.'''
    event = ftrack_api.event.base.Event('test', id='some-id')

    assert event.is_stopped() is False

    event.stop()
    assert event.is_stopped() is True


def test_is_stopped():
    '''Report stopped status of event.'''
    event = ftrack_api.event.base.Event('test', id='some-id')

    assert event.is_stopped() is False

    event.stop()
    assert event.is_stopped() is True

    event.stop()
    assert event.is_stopped() is True
