# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import pytest

import ftrack_api.event.subscription
from ftrack_api.event.base import Event


def test_string_representation():
    '''String representation is subscription expression.'''
    expression = 'topic=some-topic'
    subscription = ftrack_api.event.subscription.Subscription(expression)

    assert str(subscription) == expression


@pytest.mark.parametrize('expression, event, expected', [
    ('topic=test', Event(topic='test'), True),
    ('topic=test', Event(topic='other-test'), False)
], ids=[
    'match',
    'no match'
])
def test_includes(expression, event, expected):
    '''Subscription includes event.'''
    subscription = ftrack_api.event.subscription.Subscription(expression)
    assert subscription.includes(event) is expected
