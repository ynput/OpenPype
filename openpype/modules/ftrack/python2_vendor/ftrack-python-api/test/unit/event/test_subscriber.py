# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest

import ftrack_api.event.subscriber
from ftrack_api.event.base import Event


def test_string_representation():
    '''String representation.'''
    subscriber = ftrack_api.event.subscriber.Subscriber(
        'topic=test', lambda x: None, {'meta': 'info'}, 100
    )

    assert str(subscriber) == (
        '<Subscriber metadata={\'meta\': \'info\'} subscription="topic=test">'
    )


@pytest.mark.parametrize('expression, event, expected', [
    ('topic=test', Event(topic='test'), True),
    ('topic=test', Event(topic='other-test'), False)
], ids=[
    'interested',
    'not interested'
])
def test_interested_in(expression, event, expected):
    '''Determine if subscriber interested in event.'''
    subscriber = ftrack_api.event.subscriber.Subscriber(
        expression, lambda x: None, {'meta': 'info'}, 100
    )
    assert subscriber.interested_in(event) is expected
